import numpy
import pickle

from typing import Union

from fastapi import HTTPException
from fastapi.responses import HTMLResponse

if False:
  with open("data/availabilities/availabilities.pkl", "rb") as file:
    DATAFRAME = pickle.load(file)

  @app.get("/", response_class=HTMLResponse)
  async def query(server: Union[str, None] = None, start: Union[str, None] = None, stop: Union[str, None] = None, format: str = "csv"):
    """Query data based on server, start, stop, and format."""

    # Validate format
    formats = ["json", "csv", "html"]
    if format and format not in formats:
      emsg = f"Format must be one of {formats}"
      raise HTTPException(status_code=400, detail=emsg)

    if start is not None:
      start_dt64, emsg = _parse_time(start, 'start')
      if emsg is not None:
        raise HTTPException(status_code=400, detail=emsg)

    if stop is not None:
      stop_dt64, emsg = _parse_time(stop, 'stop')
      if emsg is not None:
        raise HTTPException(status_code=400, detail=emsg)

    # Filter data
    ql = [] # Query list
    if server is not None:
      ql.append(f'server == "{server}"')
    if start is not None:
      ql.append(f'start >= "{start_dt64}"')
    if stop is not None:
      ql.append(f'stop <= "{stop_dt64}"')

    # Query string
    qs = " & ".join(ql)
    rows = DATAFRAME.query(qs)
    if rows.empty:
      rows = DATAFRAME[DATAFRAME['server'] == server]
      unique_servers = ", ".join(DATAFRAME['server'].unique().tolist())
      if rows.empty:
        emsg = f"Invalid server. Server must be one of: {unique_servers}"
        raise HTTPException(status_code=404, detail=emsg)

    date_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    if format == "json":
      json_ = rows.to_json(index=False, orient="split", date_format='iso')
      return json_
    if format == "csv":
      return rows.to_csv(index=False, date_format=date_format).encode("utf-8")
    if format == "html":
      html_ = rows.to_html(index=False)
      return HTMLResponse(content=html_)

  def _parse_time(timestamp, which):
    from hapiclient import hapitime2datetime
    try:
      dt = hapitime2datetime(timestamp, allow_missing_Z=True)
      dt64 = numpy.datetime64(dt[0].replace(tzinfo=None))
    except:
      return None, f"Could not parse {which} with hapitime2datetime({which}, allow_missing_Z=True)"

    return dt64, None
