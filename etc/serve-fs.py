import os
import uvicorn
import utilrsw

root = os.path.join(utilrsw.script_info()['dir'], "..", "data")
app = utilrsw.servefs(root=root)
uvicorn.run(app, host="0.0.0.0", port=6001, server_header=False)