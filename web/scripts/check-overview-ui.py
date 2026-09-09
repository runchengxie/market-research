"""Browser check for overview, legacy redirect, and native research navigation."""
import sys

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(sys.argv[1], wait_until="domcontentloaded")
    cards = page.get_by_role("region", name="各专题研究进展")
    cards.wait_for(timeout=10000)
    assert cards.locator("article").count() == 3
    assert page.locator("main table, main canvas, main iframe").count() == 0
    assert page.locator('a[href*="recovery.html"]').count() == 0
    for width in [1440, 390]:
        page.set_viewport_size({"width": width, "height": 1100})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("main").screenshot(path=f"/tmp/quant-overview-{width}.png")
    page.goto(sys.argv[1] + "research/recovery.html", wait_until="domcontentloaded")
    page.wait_for_url("**/#cashflow-recovery")
    recovery = page.get_by_role("region", name="回本与持有期风险")
    recovery.wait_for()
    assert "800现金流" in recovery.inner_text()
    page.wait_for_function("Math.abs(document.querySelector('#cashflow-recovery')?.getBoundingClientRect().top ?? Infinity) < 60")
    recovery.get_by_text("计算方法与阅读提示", exact=True).click()
    assert recovery.get_by_text("回本所需涨幅等于前期高点除以当前点位，再减1。例如下跌50%后，需要上涨100%才能回本。", exact=True).is_visible()
    recovery.get_by_role("link", name="查看小微盘回本研究 ↗").click()
    page.locator('#microcap-recovery').wait_for()
    assert "同花顺微盘" in recovery.inner_text()
    page.get_by_role("button", name="跨市场小微盘流动性", exact=True).click()
    page.get_by_role("link", name="现金流历史研究", exact=True).click()
    page.locator('#cashflow-recovery').wait_for()
    recovery.get_by_role("link", name="查看小微盘回本研究 ↗").click()
    page.locator('#microcap-recovery').wait_for(timeout=10000)
    recovery.get_by_role("link", name="查看现金流回本研究 ↗").click()
    page.locator('#cashflow-recovery').wait_for()
    page.wait_for_function("Math.abs(document.querySelector('#cashflow-recovery')?.getBoundingClientRect().top ?? Infinity) < 60")
    page.get_by_role("link", name="档案总览", exact=True).click()
    cards.wait_for()
    assert page.locator("main table, main canvas").count() == 0
    assert not errors, errors
    browser.close()
    print("PASS: summary-only overview, mobile, legacy redirect, methods and cross-topic navigation")
