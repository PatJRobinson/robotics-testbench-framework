import sys
import omni.usd
import omni.kit.app
import omni.timeline

if len(sys.argv) < 2:
    raise RuntimeError("Usage: start_realisation.py <world_usd_path>")

stage_path = sys.argv[1]

ctx = omni.usd.get_context()
ctx.open_stage(stage_path)

app = omni.kit.app.get_app()
for _ in range(60):
    app.update()

timeline = omni.timeline.get_timeline_interface()
timeline.play()

print(f"[sim-platform] opened and playing: {stage_path}")
