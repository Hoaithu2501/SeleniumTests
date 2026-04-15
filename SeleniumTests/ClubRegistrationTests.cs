using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.Support.UI;
using NUnit.Framework;
using SeleniumExtras.WaitHelpers;
using System;
using System.Threading;

namespace SeleniumTests
{
    [TestFixture]
    public class ClubRegistrationTests
    {
        private IWebDriver? driver;
        private WebDriverWait? wait;
        private string url = "http://127.0.0.1:5002";

        private int slowDelay = 3000;

        [SetUp]
        public void Setup()
        {
            var options = new ChromeOptions();
            options.AddArgument("--start-maximized");
            options.AddArgument("--window-size=1920,1080");
            driver = new ChromeDriver(options);
            wait = new WebDriverWait(driver, TimeSpan.FromSeconds(20));

            driver.Navigate().GoToUrl(url + "/login");
            Thread.Sleep(2000);

            var userInp = wait.Until(ExpectedConditions.ElementIsVisible(By.Name("username")));
            userInp.SendKeys("Thư");
            Thread.Sleep(500);
            driver.FindElement(By.Name("password")).SendKeys("123456");
            Thread.Sleep(1000);

            var loginBtn = driver.FindElement(By.CssSelector("button[type='submit']"));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", loginBtn);

            Thread.Sleep(slowDelay); 
        }

        [Test]
        public void Test_00_ClubRegistration_UI_Display()
        {
            driver!.Navigate().GoToUrl(url + "/student/club/register");
            Thread.Sleep(slowDelay); 

            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("club_name"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("field"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("intended_username"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("email"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("phone"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("president_name"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("description"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.CssSelector("button[type='submit']"))), Is.Not.Null);

            Thread.Sleep(slowDelay); 
        }

        [Test]
        public void Test_01_RegSuccess()
        {
            string id = DateTime.Now.Ticks.ToString().Substring(10, 5);
            RunAction(
                "CLB Thành Công " + id,
                "Học thuật",
                "leader" + id,
                "Mô tả hoạt động CLB đầy đủ",
                "clb" + id + "@neu.edu.vn",
                "09123" + id);

            var wait = new WebDriverWait(driver!, TimeSpan.FromSeconds(15));
            wait.Until(d => d.Url.ToLower().Contains("dashboard"));

            Thread.Sleep(slowDelay); 
            Assert.That(driver!.Url.ToLower(), Does.Contain("dashboard"));
        }

        [Test]
        public void Test_06_DupUser()
        {
            RunAction("C06", "Học thuật", "Thư", "Goal 06", "", "");
            Thread.Sleep(slowDelay); 
            Assert.That(driver!.Url.ToLower(), Does.Contain("register"));
        }

        [Test]
        public void Test_07_DupClub()
        {
            RunAction("CLB Am Nhac", "Học thuật", "u7", "Goal 07", "", "");
            Thread.Sleep(slowDelay);
            Assert.That(driver!.Url.ToLower(), Does.Contain("register"));
        }

        [Test]
        public void Test_08_Cancel()
        {
            driver!.Navigate().GoToUrl(url + "/student/club/register");
            Thread.Sleep(2000);

            var cancelBtn = wait!.Until(ExpectedConditions.ElementExists(By.LinkText("Hủy bỏ")));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].scrollIntoView(true);", cancelBtn);
            Thread.Sleep(1000);

            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", cancelBtn);
            Thread.Sleep(slowDelay); 
            Assert.That(driver.Url.ToLower(), Does.Contain("dashboard"));
        }

        [Test]
        public void Test_09_NoOpt()
        {
            string id = DateTime.Now.Ticks.ToString().Substring(10, 5);
            RunAction("C09 " + id, "Học thuật", "u9_" + id, "Goal 09", "", "");

            wait!.Until(d => d.Url.ToLower().Contains("dashboard"));
            Thread.Sleep(slowDelay);
            Assert.That(driver!.Url.ToLower(), Does.Contain("dashboard"));
        }

        private void RunAction(string n, string f, string u, string m, string email, string phone)
        {
            driver!.Navigate().GoToUrl(url + "/student/club/register");
            Thread.Sleep(2000);

            var wait = new WebDriverWait(driver, TimeSpan.FromSeconds(10));

            var nameInput = wait.Until(ExpectedConditions.ElementIsVisible(By.Name("club_name")));
            nameInput.Clear();
            if (!string.IsNullOrEmpty(n)) SendKeysSlowly(nameInput, n);

            if (!string.IsNullOrEmpty(f))
            {
                var fieldSelect = driver.FindElement(By.Name("field"));
                new SelectElement(fieldSelect).SelectByText(f);
                Thread.Sleep(1000);
            }

            var userInp = driver.FindElement(By.Name("intended_username"));
            userInp.Clear();
            if (!string.IsNullOrEmpty(u)) SendKeysSlowly(userInp, u);

            var descInp = driver.FindElement(By.Name("description"));
            descInp.Clear();
            if (!string.IsNullOrEmpty(m)) SendKeysSlowly(descInp, m);

            try
            {
                if (!string.IsNullOrEmpty(email)) SendKeysSlowly(driver.FindElement(By.Name("email")), email);
                if (!string.IsNullOrEmpty(phone)) SendKeysSlowly(driver.FindElement(By.Name("phone")), phone);
            }
            catch { }

            Thread.Sleep(1000); 
            var btn = driver.FindElement(By.CssSelector("button[type='submit']"));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].scrollIntoView(true);", btn);
            Thread.Sleep(1000);
            btn.Click();
        }

        private void SendKeysSlowly(IWebElement element, string value)
        {
            foreach (var character in value)
            {
                element.SendKeys(character.ToString());
                Thread.Sleep(150); 
            }
            Thread.Sleep(300); 
        }

        [TearDown]
        public void Close()
        {
            if (driver != null)
            {
                Thread.Sleep(slowDelay); 
                driver.Quit();
                driver.Dispose();
            }
        }
    }
}