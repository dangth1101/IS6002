from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.parametrize("entrypoint",["app.py","pages/1_BIRD_VN_Robust_50.py","pages/2_BIRD_VN_Analysis.py","pages/3_BIRD_VN_Validation_Review.py","pages/4_BIRD_VN_Reports.py"])
def test_streamlit_pages_smoke_without_provider_calls(entrypoint):
    app=AppTest.from_file(ROOT/"app.py",default_timeout=30).run()
    if entrypoint!="app.py":app.switch_page(str(ROOT/entrypoint)).run()
    assert not app.exception, [item.message for item in app.exception]
    if entrypoint.endswith("1_BIRD_VN_Robust_50.py"):
        assert app.session_state["birdvn_demo_runs"]==[]
