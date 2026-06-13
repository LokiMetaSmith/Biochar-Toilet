import asyncio
from playwright.async_api import async_playwright
import re

async def main():
    with open('Presentations/Biochar_Toilet_Slide_Deck.html', 'r') as f:
        html = f.read()

    # Let's adjust the styling for Slide 14.1
    # We will find the specific slide and replace its inline styles.
    # The slide starts with <!-- Slide 14.1: Induction Hardware Deep Dive -->
    slide_pattern = re.compile(
        r'(<!-- Slide 14.1: Induction Hardware Deep Dive -->.*?<div class="bleed-text-side">.*?)(<h2.*?</ul>)',
        re.DOTALL
    )

    replacement = r"""\1
        <h2 class="slide-title" style="margin-bottom: 10px; font-size: 1.8rem;">Induction Hardware: Current Development Status</h2>
        <div class="content-area" style="font-size: 0.8rem; line-height: 1.3;">
            <p style="margin-bottom: 10px;">
                The Phase 2 induction architecture is nearing its first integrated
                test cycle. Major subsystems have been fabricated and assembled,
                with final vessel integration currently underway.
            </p>
            <ul style="margin-top: 5px; margin-bottom: 0; padding-left: 20px;">
                <li style="margin-bottom: 6px;">
                    <strong>Copper Induction Coil:</strong>
                    A formed hollow copper coil has been fabricated to deliver
                    contactless energy directly to the processing chamber.
                </li>
                <li style="margin-bottom: 6px;">
                    <strong>Nested Vessel Assembly:</strong>
                    The prototype utilizes inner and outer vessels integrated
                    within a modified pressure pot to evaluate thermal performance
                    and sealing strategies.
                </li>
                <li style="margin-bottom: 6px;">
                    <strong>Thermal Insulation:</strong>
                    Rockwool insulation lines the vessel walls, while an insulated
                    base minimizes heat loss and improves energy efficiency.
                </li>
                <li style="margin-bottom: 6px;">
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
"""

    modified_html = re.sub(r'(<!-- Slide 14.1: Induction Hardware Deep Dive -->\s*<div class="slide-container bleed-image-layout">\s*<div class="bleed-text-side">)(.*?)(\s*</div>\s*<div class="bleed-image-side"|<!-- Slide 14.2)', replacement, html, flags=re.DOTALL)

    # Let's also patch the bleed-text-side specifically for this slide to reduce padding
    # Actually, bleed-text-side padding is set by CSS: .bleed-text-side { padding: 80px 60px; ... }
    # Let's add an inline style to this specific slide's bleed-text-side
    modified_html = modified_html.replace(
        '<!-- Slide 14.1: Induction Hardware Deep Dive -->\n<div class="slide-container bleed-image-layout">\n    <div class="bleed-text-side">',
        '<!-- Slide 14.1: Induction Hardware Deep Dive -->\n<div class="slide-container bleed-image-layout">\n    <div class="bleed-text-side" style="padding: 40px 40px;">'
    )

    with open('/tmp/test_deck.html', 'w') as f:
        f.write(modified_html)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.goto("file:///tmp/test_deck.html")

        # Navigate to Slide 14.1 (index depends on how many slides there are, but we can just find it and screenshot the container)
        slide_element = await page.query_selector("text=Induction Hardware: Current Development Status")
        if slide_element:
            # Get the parent slide-container
            container = await slide_element.evaluate_handle('el => el.closest(".slide-container")')
            await container.screenshot(path='/tmp/test_slide9.png')
            print("Screenshot saved to /tmp/test_slide9.png")
        else:
            print("Slide not found")
        await browser.close()

asyncio.run(main())
