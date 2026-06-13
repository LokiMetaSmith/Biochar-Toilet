import asyncio
from playwright.async_api import async_playwright

async def main():
    with open('Presentations/Biochar_Toilet_Slide_Deck.html', 'r') as f:
        html = f.read()

    target_original = """<!-- Slide 14.1: Induction Hardware Deep Dive -->
<div class="slide-container bleed-image-layout">
    <div class="bleed-text-side">
        <h2 class="slide-title">Induction Hardware: Current Development Status</h2>
        <div class="content-area">
            <p>
                The Phase 2 induction architecture is nearing its first integrated
                test cycle. Major subsystems have been fabricated and assembled,
                with final vessel integration currently underway.
            </p>
            <ul style="margin-top: 20px; line-height: 1.6;">
                <li>
                    <strong>Copper Induction Coil:</strong>
                    A formed hollow copper coil has been fabricated to deliver
                    contactless energy directly to the processing chamber.
                </li>
                <li>
                    <strong>Nested Vessel Assembly:</strong>
                    The prototype utilizes inner and outer vessels integrated
                    within a modified pressure pot to evaluate thermal performance
                    and sealing strategies.
                </li>
                <li>
                    <strong>Thermal Insulation:</strong>
                    Rockwool insulation lines the vessel walls, while an insulated
                    base minimizes heat loss and improves energy efficiency.
                </li>
                <li>
                    <strong>Coil Isolation:</strong>
                    The current design electrically isolates the induction coil
                    using Kapton tape. Future iterations may transition to a
                    modular ceramic coil assembly to improve manufacturability,
                    durability, and serviceability.
                </li>
                <li>
                    <strong>Next Milestone:</strong>
                    Final bulkhead integration and vessel sealing will enable
                    the first fully assembled induction test runs and validation
                    of the complete thermal process.
                </li>
            </ul>
        </div>
    </div>"""

    target_replacement = """<!-- Slide 14.1: Induction Hardware Deep Dive -->
<div class="slide-container bleed-image-layout">
    <div class="bleed-text-side" style="padding: 20px 40px; justify-content: center;">
        <h2 class="slide-title" style="font-size: 24px; margin-bottom: 8px; margin-top: 0; line-height: 1.1;">Induction Hardware: Current Development Status</h2>
        <div class="content-area" style="font-size: 14px; line-height: 1.3;">
            <p style="margin-bottom: 8px;">
                The Phase 2 induction architecture is nearing its first integrated
                test cycle. Major subsystems have been fabricated and assembled,
                with final vessel integration currently underway.
            </p>
            <ul style="margin-top: 0; margin-bottom: 0; padding-left: 15px;">
                <li style="margin-bottom: 4px;">
                    <strong>Copper Induction Coil:</strong>
                    A formed hollow copper coil has been fabricated to deliver
                    contactless energy directly to the processing chamber.
                </li>
                <li style="margin-bottom: 4px;">
                    <strong>Nested Vessel Assembly:</strong>
                    The prototype utilizes inner and outer vessels integrated
                    within a modified pressure pot to evaluate thermal performance
                    and sealing strategies.
                </li>
                <li style="margin-bottom: 4px;">
                    <strong>Thermal Insulation:</strong>
                    Rockwool insulation lines the vessel walls, while an insulated
                    base minimizes heat loss and improves energy efficiency.
                </li>
                <li style="margin-bottom: 4px;">
                    <strong>Coil Isolation:</strong>
                    The current design electrically isolates the induction coil
                    using Kapton tape. Future iterations may transition to a
                    modular ceramic coil assembly to improve manufacturability,
                    durability, and serviceability.
                </li>
                <li style="margin-bottom: 0;">
                    <strong>Next Milestone:</strong>
                    Final bulkhead integration and vessel sealing will enable
                    the first fully assembled induction test runs and validation
                    of the complete thermal process.
                </li>
            </ul>
        </div>
    </div>"""

    if target_original in html:
        modified_html = html.replace(target_original, target_replacement)
        with open('/tmp/test_deck8.html', 'w') as f:
            f.write(modified_html)

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1280, "height": 720})
            await page.goto("file:///tmp/test_deck8.html")
            await page.wait_for_timeout(500)

            slide_element = await page.query_selector("text=Induction Hardware: Current Development Status")
            if slide_element:
                container = await slide_element.evaluate_handle('el => el.closest(".slide-container")')
                await container.screenshot(path='/tmp/test_slide16.png')
                print("Screenshot saved to /tmp/test_slide16.png")
            else:
                print("Slide not found")
            await browser.close()
    else:
        print("Original target not found in HTML")

asyncio.run(main())
