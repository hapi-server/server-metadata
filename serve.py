import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from starlette.responses import StreamingResponse
import os
import datetime
import urllib.parse
import html

app = FastAPI()

BASE_DIR = Path(".")  # Base directory to serve
STREAM_THRESHOLD = 10 * 1024 * 1024  # 10 MB threshold for streaming

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "HEAD"],
    allow_headers=["Content-Type"]
)

@app.get("/{path:path}", response_class=HTMLResponse)
async def serve_directory_or_file(path: str = ""):
    """Serve directory listing or a file."""
    full_path = BASE_DIR / path

    if full_path.is_file():
      if full_path.stat().st_size < STREAM_THRESHOLD:
        return FileResponse(full_path)
      else:
        # If the file is larger than 10 MB, stream it
        def iterfile(full_path):
          with open(full_path, mode="rb") as file_like:
            yield from file_like
        return StreamingResponse(iterfile(full_path))

    # If the path is not a directory, raise a 404 error
    if not full_path.is_dir():
        raise HTTPException(status_code=404, detail="File or directory not found")

    # Generate directory listing
    try:
        items = os.listdir(full_path)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return HTMLResponse(content=_dir_listing(path, items))

@app.head("/{path:path}")
async def head_request(path: str = ""):
    """Handle HEAD requests."""
    full_path = BASE_DIR / path

    # If the path is a file, return headers only
    if full_path.is_file():
        return FileResponse(full_path, headers={"Content-Length": str(full_path.stat().st_size)})

    # If the path is not a directory, raise a 404 error
    if not full_path.is_dir():
        raise HTTPException(status_code=404, detail="File or directory not found")

    # For directories, return a generic response with no body
    return HTMLResponse(content="", headers={"Content-Type": "text/html"})

_DIR_LISTING = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta http-equiv="Content-type" content="text/html;charset=UTF-8">
  <title>__DIRECTORY__</title>
</head>
<body>
  <table>
    <thead>
      <tr>
        <th>Name</th>
        <th>Size</th>
        <th>Last Modified</th>
      </tr>
    </thead>
    <tbody>
__DIRECTORY_HTML__
    </tbody>
  </table>
</body>
</html>
"""

def _dir_listing(path, items):

  items.sort(key=lambda a: a.lower())
  rows = []
  displaypath = html.escape(urllib.parse.unquote(path), quote=False)

  for name in items:
      fullname = Path(path) / name
      size = fullname.stat().st_size
      displayname = linkname = name

      # Append / for directories or @ for symbolic links
      if fullname.is_dir():
          displayname = name + "/"
          linkname = name + "/"
      if fullname.is_symlink():
          displayname = name + "@"

      href = urllib.parse.quote(linkname, errors="surrogatepass")
      text = html.escape(displayname, quote=False)
      modified = datetime.datetime.fromtimestamp(fullname.stat().st_mtime)
      modified = modified.strftime('%Y-%m-%dT%H:%M:%SZ')
      a = f'<a href="{href}">{text}</a>'
      rows.append(f'      <tr><td>{a}</td><td>{size}</td><td>{modified}</td></tr>')

  # Replace placeholders in the template
  listing_html = _DIR_LISTING.replace("__DIRECTORY__", displaypath)
  listing_html = listing_html.replace("__DIRECTORY_HTML__", "\n".join(rows))
  return listing_html

if __name__ == '__main__':
    uvicorn.run(app=app, host="0.0.0.0", port=6001, server_header=False)