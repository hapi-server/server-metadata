import uvicorn
import utilrsw

app = utilrsw.servefs(root="data")
if __name__ == "__main__":
  uvicorn.run(app, host="0.0.0.0", port=6001, server_header=False)
