"""Check native replication evidence without publishing or changing research inputs."""
import sys

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(sys.argv[1], wait_until="domcontentloaded")
    page.get_by_role("region", name="各专题研究进展").wait_for()
    assert page.locator("main table").count() == 0
    page.get_by_role("link", name="现金流历史研究", exact=True).click()
    research = page.get_by_role("region", name="指数复刻进展")
    research.wait_for()
    assert research.locator("article").count() == 4
    assert "12.27%" in research.inner_text()
    assert "0.9804" in research.inner_text()
    assert "2021-03-15" in research.inner_text()
    for width in (1440, 390):
        page.set_viewport_size({"width": width, "height": 1100})
        page.wait_for_function("document.documentElement.scrollWidth <= innerWidth + 1")
        research.screenshot(path=f"/tmp/quant-replication-{width}.png")
    page.get_by_role("link", name="小微盘历史研究", exact=True).click()
    research.wait_for()
    assert research.locator("article").count() == 2
    assert research.locator("table").count() == 0
    assert "万得微盘" in research.inner_text()
    research.get_by_text("数据来源与研究边界", exact=True).click()
    assert "189" in research.inner_text()
    assert not errors, errors
    for body, status in [("unavailable", 503), ('{"schema_version":1}', 200)]:
        failure = browser.new_page()
        failure.route("**/data/research/replication.json", lambda route: route.fulfill(status=status, body=body))
        failure.goto(sys.argv[1] + "#cashflow", wait_until="domcontentloaded")
        failure.get_by_text("复刻研究数据暂不可用，请稍后重试。其他专题数据仍可查看。", exact=True).wait_for()
        assert failure.get_by_role("region", name="指数复刻进展").count() == 0
        failure.close()
    browser.close()
    print("PASS: native replication data, topic isolation, mobile, missing/malformed snapshots")
