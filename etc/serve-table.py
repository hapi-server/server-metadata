import os
import tableui

script_dir = os.path.dirname(os.path.abspath(__file__))
config = os.path.join(script_dir, "..", "table", "tableui.json")
tableui.serve(config=config, port=6002)
