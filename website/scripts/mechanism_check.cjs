const {chromium} = require(process.argv[2] || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname,'..');
(async () => {
  const browser = await chromium.launch({headless:true,executablePath:process.argv[3]});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(process.env.SITE_URL || 'http://127.0.0.1:8765/astra-guide-vla-website/');
    const board=page.locator('.mechanism');
    await board.scrollIntoViewIfNeeded();
    await page.waitForTimeout(2200);
    assert.equal(await board.getAttribute('data-phase'),'0','Start deliberately, not mid-story on entry');
    await page.locator('#motion-play').click();
    await page.waitForFunction(()=>document.querySelector('.mechanism').dataset.phase==='3');
    await page.locator('#motion-play').click();
    assert.equal(await page.locator('[data-lane=baseline]').getAttribute('data-controls'),'16');
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-controls'),'16');
    await page.waitForTimeout(2200);
    assert.equal(await board.getAttribute('data-phase'),'3','Pause must stop both rows');
    for(let i=0;i<3;i++) await page.locator('#motion-next').click();
    assert.equal(await page.locator('[data-lane=baseline]').getAttribute('data-controls'),'32');
    assert.equal(await page.locator('[data-lane=baseline]').getAttribute('data-state'),'review');
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-controls'),'64');
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-state'),'execute');
    assert.equal(await board.locator('.stage-card.current').count(),2);
    assert.equal(await page.locator('[data-lane=baseline] .current-marker:visible').count(),1);
    assert.equal(await page.locator('[data-lane=harness] .current-marker:visible').count(),1);
    for(const width of [1440,768,375]) {
      await page.setViewportSize({width,height:1000});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      await board.screenshot({path:path.join(root,`.cache/comparison-${width}.png`)});
    }
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('#motion-prev').click();
    assert.equal(await board.getAttribute('data-phase'),'5');
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-controls'),'48');
    for(let i=5;i<9;i++) await page.locator('#motion-next').click();
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-state'),'review','Budget exhaustion alone is not success');
    await page.locator('#motion-next').click();
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-state'),'done');
    assert.equal(await page.locator('[data-lane=baseline]').getAttribute('data-state'),'review');
    assert.match(await page.locator('[data-lane=harness] .lane-status').textContent(),/Task complete/);
    for(const width of [1440,768,375]) {
      await page.setViewportSize({width,height:1000});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      await board.screenshot({path:path.join(root,`.cache/completion-${width}.png`)});
    }
    await page.setViewportSize({width:1440,height:1000});
    for(let i=10;i<17;i++) {
      await page.locator('#motion-next').click();
      assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-state'),'done','Finished row never waits for the other row');
    }
    assert.equal(await page.locator('[data-lane=baseline]').getAttribute('data-state'),'done');
    await page.getByRole('button',{name:'Monitor event',exact:true}).click();
    for(let i=0;i<6;i++) await page.locator('#motion-next').click();
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-controls'),'64');
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-state'),'review');
    assert.match(await page.locator('#phase-caption').textContent(),/earlier review/);
    await page.locator('#motion-next').click();
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-controls'),'64','Authorization precedes resumed execution');
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-state'),'authorized');
    assert.equal(await page.locator('#budget-value').textContent(),'0 / 40 controls');
    await page.locator('#motion-next').click();
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-state'),'execute');
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-controls'),'80');
    assert.equal(await page.locator('#budget-value').textContent(),'16 / 40 controls');
    for(let i=8;i<11;i++) await page.locator('#motion-next').click();
    assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-state'),'done');
    assert.equal(await page.locator('[data-lane=baseline]').getAttribute('data-state'),'execute');
    assert.equal(await page.locator('#budget-value').textContent(),'36 / 40 controls','Success ends execution without consuming unused budget');
    for(let i=11;i<17;i++) {
      await page.locator('#motion-next').click();
      assert.equal(await page.locator('[data-lane=harness]').getAttribute('data-state'),'done');
    }
    for(const lane of ['harness','baseline']) {
      assert.equal(await page.locator(`[data-lane=${lane}]`).getAttribute('data-controls'),'100');
      assert.equal(await page.locator(`[data-lane=${lane}]`).getAttribute('data-state'),'done');
      assert.equal(await page.locator(`[data-lane=${lane}] .current-marker:visible`).textContent(),'FINISHED');
    }
    assert.equal(await page.locator('#motion-next').isDisabled(),true);
    assert.equal(await page.locator('#motion-play').textContent(),'Replay both');
    await page.locator('#motion-play').click();
    assert.equal(await board.getAttribute('data-phase'),'0');
    await page.locator('#motion-reset').click();
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.locator('#motion-next').focus();
    await page.keyboard.press('Enter');
    assert.equal(await board.getAttribute('data-phase'),'1');
    await page.waitForTimeout(2200);
    assert.equal(await board.getAttribute('data-phase'),'1');
    assert.deepEqual(errors,[]);
    console.log('PASS: shared start/pause, independent completion in both paths, explicit monitor reauthorization, cumulative controls and renewed budget, terminal states, previous/reset/replay, keyboard/reduced motion, 1440/768/375px.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
