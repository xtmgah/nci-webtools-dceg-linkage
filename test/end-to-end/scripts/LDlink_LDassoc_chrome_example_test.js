
const assert = require('assert');
const path = require('path');
const test = require('selenium-webdriver/testing');
const webdriver = require('selenium-webdriver'),
By = webdriver.By,
until = webdriver.until;

describe(path.basename(__filename), function() {
  // --enter test case name (ie. 'example test case')
  test.it('LDlink_LDassoc_chrome_example_test', function(done) {
    this.timeout(0);
    var driver = new webdriver.Builder()
    .forBrowser('chrome')
    .build();

    // -----example get path of example test file----- 
    // --enter name of example input files folder in main directory (ie. 'examples')  
    // let examplesDirectory = __dirname.split(path.sep).concat(['examples']);

    // --enter name of file (ie. 'study2.txt')
    // driver.findElement(By.id("study_1")).sendKeys(examplesDirectory.concat(['study2.txt']).join(path.sep)).then(function() {
    //   driver.sleep(1000);
    // });

    driver.get("https://analysistools-sandbox.nci.nih.gov"+"/");
		driver.sleep('2000');
		driver.findElement(By.linkText("LDLink")).click();
		driver.sleep('2000');
		driver.findElement(By.id("ldassoc-tab-anchor")).click();
		driver.sleep('2000');
		driver.findElement(By.css("span.slider.round")).click();
		driver.sleep('2000');
		driver.findElement(By.id("ldassoc")).click();
		driver.sleep('8000');
		driver.findElement(By.css("div.bk-canvas-events")).getText().then(text=> {
			assert(text == '');
			done();
		});
		

    driver.close();
  });
})
