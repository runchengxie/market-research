from market_research.cli import _build_parser


def test_study_report_commands_exist():
    parser = _build_parser()
    assert parser.parse_args(["report", "style-factors", "--study", "study.yml"]).report_command == "style-factors"
    assert parser.parse_args(["report", "global-six-market", "--study", "study.yml"]).report_command == "global-six-market"
