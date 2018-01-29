
const assert = require('assert');
const path = require('path');
const test = require('selenium-webdriver/testing');
const webdriver = require('selenium-webdriver'),
By = webdriver.By,
until = webdriver.until;

describe(path.basename(__filename), function() {
  // --enter test case name (ie. 'example test case')
  test.it('ldlink_help_text_test', function(done) {
    this.timeout(0);
    var driver = new webdriver.Builder()
    .forBrowser('firefox')
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
		driver.findElement(By.id("help-tab-anchor")).click();
		driver.sleep('2000');
		driver.findElement(By.css("#help-tab > p")).getText().then(text=> {
			assert(text == 'LDlink is designed to be an intuitive and simple tool for investigating patterns of linkage disequilibrium across a variety of ancestral population groups. This help documentation page gives detailed description of the metrics calculated by LDlink modules and aids users in understanding all aspects of the required input and returned output. The documentation is divided into the following sections:');
			done();
		});
		

    driver.close();
  });
})
