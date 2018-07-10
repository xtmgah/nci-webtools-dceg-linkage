
const assert = require('assert');
const path = require('path');
const test = require('selenium-webdriver/testing');
const webdriver = require('selenium-webdriver'),
By = webdriver.By,
until = webdriver.until;

describe(path.basename(__filename), function() {
  // --enter test case name (ie. 'example test case')
  test.it('example_wikipedia_test', function(done) {
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

    driver.get("https://www.wikipedia.org"+"/");
		driver.sleep('2000');
		driver.findElement(By.id("searchInput")).sendKeys('selenium');
		driver.sleep('2000');
		driver.findElement(By.css("button.pure-button.pure-button-primary-progressive")).click();
		driver.sleep('3000');
		driver.getTitle().then(title=> {
			assert(title == 'Selenium - Wikipedia');
			done();
		});
		

    driver.close();
  });
})
