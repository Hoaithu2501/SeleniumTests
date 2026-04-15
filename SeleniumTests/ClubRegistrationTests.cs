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

        [SetUp]
        public void Setup()
        {
            var options = new ChromeOptions();
            options.AddArgument("--start-maximized");
            options.AddArgument("--window-size=1920,1080");
            driver = new ChromeDriver(options);
            wait = new WebDriverWait(driver, TimeSpan.FromSeconds(20));

            driver.Navigate().GoToUrl(url + "/login");
            var userInp = wait.Until(ExpectedConditions.ElementIsVisible(By.Name("username")));
            userInp.SendKeys("Thư");
            driver.FindElement(By.Name("password")).SendKeys("123456");

            var loginBtn = driver.FindElement(By.CssSelector("button[type='submit']"));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", loginBtn);

            Thread.Sleep(3000);
        }

        [Test]
        public void Test_00_ClubRegistration_UI_Display()
        {
            driver!.Navigate().GoToUrl(url + "/student/club/register");

            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("club_name"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("field"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("intended_username"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("email"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("phone"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("president_name"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.Name("description"))), Is.Not.Null);
            Assert.That(wait!.Until(driver => driver.FindElement(By.CssSelector("button[type='submit']"))), Is.Not.Null);
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

            var wait = new WebDriverWait(driver, TimeSpan.FromSeconds(15));
            wait!.Until(d => d.Url.ToLower().Contains("dashboard"));

            Assert.That(driver!.Url.ToLower(), Does.Contain("dashboard"));
        }

        [Test]
        public void Test_06_DupUser()
        {
            RunAction("C06", "Học thuật", "Thư", "Goal 06", "", "");
            Assert.That(driver!.Url.ToLower(), Does.Contain("register"));
        }

        [Test]
        public void Test_07_DupClub()
        {
            RunAction("CLB Am Nhac", "Học thuật", "u7", "Goal 07", "", "");
            Assert.That(driver!.Url.ToLower(), Does.Contain("register"));
        }

        [Test]
        public void Test_08_Cancel()
        {
            driver!.Navigate().GoToUrl(url + "/student/club/register");
            var cancelBtn = wait!.Until(ExpectedConditions.ElementExists(By.LinkText("Hủy bỏ")));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", cancelBtn);
            Thread.Sleep(2000);
            Assert.That(driver.Url.ToLower(), Does.Contain("dashboard"));
        }

        [Test]
        public void Test_09_NoOpt()
        {
            string id = DateTime.Now.Ticks.ToString().Substring(10, 5);
            RunAction("C09 " + id, "Học thuật", "u9_" + id, "Goal 09", "", "");

            wait!.Until(d => d.Url.ToLower().Contains("dashboard"));

            Assert.That(driver!.Url.ToLower(), Does.Contain("dashboard"));
        }


        private void RunAction(string n, string f, string u, string m, string email, string phone)
        {
            driver!.Navigate().GoToUrl(url + "/student/club/register");
            var wait = new WebDriverWait(driver, TimeSpan.FromSeconds(10));
            var nameInput = wait.Until(ExpectedConditions.ElementIsVisible(By.Name("club_name")));
            nameInput.Clear();
            if (!string.IsNullOrEmpty(n)) nameInput.SendKeys(n);
            if (!string.IsNullOrEmpty(f))
            {
                new SelectElement(driver.FindElement(By.Name("field"))).SelectByText(f);
            }
            var userInp = driver.FindElement(By.Name("intended_username"));
            userInp.Clear();
            if (!string.IsNullOrEmpty(u)) userInp.SendKeys(u);
            var descInp = driver.FindElement(By.Name("description"));
            descInp.Clear();
            if (!string.IsNullOrEmpty(m)) descInp.SendKeys(m);
            try
            {
                if (!string.IsNullOrEmpty(email)) driver.FindElement(By.Name("email")).SendKeys(email);
                if (!string.IsNullOrEmpty(phone)) driver.FindElement(By.Name("phone")).SendKeys(phone);
            }
            catch { }
            var btn = driver.FindElement(By.CssSelector("button[type='submit']"));
            // Thay thế 2 dòng ExecuteScript click bằng dòng này:
            btn.Click();
        }

        private void SendKeysSlowly(IWebElement element, string value)
        {
            foreach (var character in value)
            {
                element.SendKeys(character.ToString());
                Thread.Sleep(1000); 
            }
            Thread.Sleep(5000); 
        }

        [TearDown]
        public void Close()
        {
            if (driver != null) { driver.Quit(); driver.Dispose(); }
        }
    }
}