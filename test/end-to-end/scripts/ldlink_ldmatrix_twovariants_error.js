
const assert = require('assert');
const path = require('path');
const test = require('selenium-webdriver/testing');
const webdriver = require('selenium-webdriver'),
By = webdriver.By,
until = webdriver.until;

describe(path.basename(__filename), function() {
  // --enter test case name (ie. 'example test case')
  test.it('ldlink_ldmatrix_twovariants_error', function(done) {
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
		driver.findElement(By.id("ldmatrix-tab-anchor")).click();
		driver.sleep('2000');
		driver.findElement(By.id("ldmatrix-file-snp-numbers")).sendKeys('rs1231234');
		driver.sleep('2000');
		driver.findElement(By.xpath("(//button[@type='button'])[7]")).click();
		driver.sleep('2000');
		driver.findElement(By.xpath("(//input[@value='YRI'])[3]")).click();
		driver.sleep('2000');
		driver.findElement(By.id("ldmatrix")).click();
		driver.sleep('2000');
		driver.findElement(By.id("ldmatrix-message-content")).getText().then(text=> {
			assert(text == 'Less than two variants to plot.');
			done();
		});
		driver.sleep('2000');
		

    driver.close();
  });
})
