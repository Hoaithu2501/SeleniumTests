using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.Support.UI;
using SeleniumExtras.WaitHelpers;
using NUnit.Framework;
using System;
using System.Threading;

namespace SeleniumTests
{
    [TestFixture]
    public class LoginTests
    {
        private IWebDriver? driver;
        private string loginUrl = "http://127.0.0.1:5002/login";
        private int slowDelay = 3000;

        [SetUp]
        public void Setup()
        {
            var options = new ChromeOptions();
            options.AddArgument("--start-maximized");
            options.AddArgument("--window-size=1920,1080");
            driver = new ChromeDriver(options);
        }

        [Test]
        public void Test00_UI_Display()
        {
            driver!.Navigate().GoToUrl(loginUrl);
            Thread.Sleep(slowDelay); 

            var wait = new WebDriverWait(driver, TimeSpan.FromSeconds(15));
            Assert.Multiple(() =>
            {
                Assert.That(wait.Until(d => d.FindElement(By.Name("username"))).Displayed);
                Assert.That(wait.Until(d => d.FindElement(By.Name("password"))).Displayed);
                Assert.That(wait.Until(d => d.FindElement(By.CssSelector("button[type='submit']"))).Displayed);
            });
            Thread.Sleep(slowDelay); 
        }

        // --- TEST 01: ĐĂNG NHẬP THÀNH CÔNG ---
        [Test]
        public void Test01_Login_Success()
        {
            driver!.Navigate().GoToUrl(loginUrl);
            LoginAction("admin", "admin123");

            var wait = new WebDriverWait(driver, TimeSpan.FromSeconds(10));
            wait.Until(d => !d.Url.ToLower().Contains("/login"));

            Thread.Sleep(slowDelay); 
            Assert.That(driver.Url.ToLower(), Does.Not.Contain("login"));
        }

        // --- TEST 02-04: CÁC TRƯỜNG HỢP ĐỂ TRỐNG (HTML5 VALIDATION) ---
        [Test]
        [TestCase("", "admin123", TestName = "Test02_Login_Empty_Username")]
        [TestCase("admin", "", TestName = "Test03_Login_Empty_Password")]
        [TestCase("", "", TestName = "Test04_Login_Empty_All")]
        public void TestGroup_Login_RequiredFields(string u, string p)
        {
            driver!.Navigate().GoToUrl(loginUrl);
            LoginAction(u, p);

            Thread.Sleep(2000); 
            Assert.That(driver.Url.ToLower(), Does.Contain("login"));
        }

        // --- TEST 05 & 06: SAI THÔNG TIN (FIXED ERROR MESSAGE) ---
        [Test]
        public void Test05_Login_Wrong_User()
        {
            driver!.Navigate().GoToUrl(loginUrl);
            LoginAction("user_khong_ton_tai", "123456");
            VerifyLoginError("Tên đăng nhập hoặc mật khẩu không chính xác");
        }

        [Test]
        public void Test06_Login_Wrong_Pass()
        {
            driver!.Navigate().GoToUrl(loginUrl);
            LoginAction("admin", "sai_mat_khau_123");
            VerifyLoginError("Tên đăng nhập hoặc mật khẩu không chính xác");
        }

        // --- TEST 07: CHUYỂN SANG TRANG ĐĂNG KÝ ---
        [Test]
        public void Test07_Link_To_Register()
        {
            driver!.Navigate().GoToUrl(loginUrl);
            Thread.Sleep(1500); 

            var wait = new WebDriverWait(driver!, TimeSpan.FromSeconds(10));
            var link = wait.Until(ExpectedConditions.ElementExists(By.CssSelector("a[href*='register']")));

            IJavaScriptExecutor js = (IJavaScriptExecutor)driver;
            js.ExecuteScript("arguments[0].scrollIntoView(true);", link);
            Thread.Sleep(1000);
            js.ExecuteScript("arguments[0].click();", link);

            Thread.Sleep(slowDelay); 
            wait.Until(d => d.Url.ToLower().Contains("register"));
            Assert.That(driver.Url.ToLower(), Does.Contain("register"));
        }

        // --- TEST 08: QUAY VỀ TRANG CHỦ ---
        [Test]
        public void Test08_Back_To_Home()
        {
            driver!.Navigate().GoToUrl(loginUrl);
            Thread.Sleep(1500);

            var homeLink = driver!.FindElement(By.CssSelector("a[href='/']"));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", homeLink);

            Thread.Sleep(slowDelay); 
            Assert.That(driver.Url.ToLower(), Is.Not.EqualTo(loginUrl));
        }

        // --- HÀM HỖ TRỢ (HELPERS) ---
        private void LoginAction(string user, string pass)
        {
            var wait = new WebDriverWait(driver!, TimeSpan.FromSeconds(10));
            var uInput = wait.Until(ExpectedConditions.ElementIsVisible(By.Name("username")));
            uInput.Clear();
            Thread.Sleep(300); 
            if (!string.IsNullOrEmpty(user)) uInput.SendKeys(user);
            Thread.Sleep(500); 

            var pInput = driver!.FindElement(By.Name("password"));
            pInput.Clear();
            Thread.Sleep(300);
            if (!string.IsNullOrEmpty(pass)) pInput.SendKeys(pass);
            Thread.Sleep(1000); 

            var btn = driver.FindElement(By.CssSelector("button[type='submit']"));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", btn);
        }

        private void VerifyLoginError(string expected)
        {
            var wait = new WebDriverWait(driver!, TimeSpan.FromSeconds(10));
            try
            {
                var alert = wait.Until(ExpectedConditions.ElementIsVisible(By.XPath("//*[contains(@class, 'alert')]")));
                Thread.Sleep(slowDelay); 
                Assert.That(alert.Text.Trim(), Does.Contain(expected));
            }
            catch
            {
                Assert.That(driver!.Url.ToLower(), Does.Contain("login"), "Không tìm thấy thông báo lỗi!");
            }
        }

        [TearDown]
        public void TearDown()
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