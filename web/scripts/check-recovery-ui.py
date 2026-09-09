"""Optional real-browser smoke test: uv run --with playwright python web/scripts/check-recovery-ui.py URL."""
import sys

from playwright.sync_api import sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(sys.argv[1], wait_until="domcontentloaded")
    recovery = page.get_by_role("region", name="回本与持有期风险")
    recovery.wait_for()
    assert "800现金流" in recovery.inner_text()
    recovery.get_by_role("button", name="微盘与小盘对照 · 供应商点位").click()
    assert "同花顺微盘" in recovery.inner_text()
    assert "800现金流" not in recovery.inner_text()
    page.get_by_role("link", name="现金流历史研究", exact=True).click()
    recovery.wait_for()
    assert "1,073 天" in recovery.inner_text()
    recovery.get_by_label("查看指数").select_option("932369.CSI")
    assert "水下区间时长 · 1000现金流" in recovery.inner_text()
    assert "2,285 天" in recovery.inner_text()
    recovery.get_by_role("button", name="现金流 · 税前全收益", exact=True).click()
    assert "税前全收益）" in recovery.get_by_label("查看指数").inner_text()
    recovery.screenshot(path="/tmp/quant-inline-recovery-cashflow.png")
    page.get_by_role("link", name="小微盘历史研究", exact=True).click()
    recovery.wait_for()
    assert recovery.get_by_label("查看指数").input_value() == "883418.TI"
    assert "308 天" in recovery.inner_text()
    assert "N/A" in recovery.inner_text()
    for width in [1440, 390]:
        page.set_viewport_size({"width": width, "height": 1100})
        page.wait_for_timeout(300)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"Page overflow at {width}"
        recovery.screenshot(path=f"/tmp/quant-inline-recovery-microcap-{width}.png")
    assert page.locator("iframe").count() == 0
    page.get_by_role("button", name="跨市场小微盘流动性", exact=True).click()
    assert recovery.count() == 0
    assert not errors, errors
    failure = browser.new_page()
    failure.route("**/data/research/recovery.json", lambda route: route.fulfill(status=503, body="unavailable"))
    failure.goto(sys.argv[1] + "#cashflow", wait_until="domcontentloaded")
    failure.get_by_role("alert").filter(has_text="回本数据加载失败").wait_for()
    malformed = browser.new_page()
    malformed.route("**/data/research/recovery.json", lambda route: route.fulfill(
        content_type="application/json", body='{"schema_version":1,"series":[null],"issues":[],"excluded":[]}'))
    malformed.goto(sys.argv[1] + "#cashflow", wait_until="domcontentloaded")
    malformed.get_by_role("alert").filter(has_text="回本数据加载失败").wait_for()
    browser.close()
    print("PASS: overview groups, cashflow basis/selection, microcap scope, mobile layout, no iframe, fetch failure")
