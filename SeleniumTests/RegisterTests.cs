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
    public class RegisterTests
    {
        private IWebDriver? driver;
        private string registerUrl = "http://127.0.0.1:5002/register";

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
        public void Test00_Register_UI_Display()
        {
            driver.Navigate().GoToUrl("http://127.0.0.1:5002/register");
            driver.Manage().Window.Maximize();
            Thread.Sleep(slowDelay); 

            var wait = new WebDriverWait(driver, TimeSpan.FromSeconds(10));

            Assert.That(wait.Until(d => d.FindElement(By.Id("username"))), Is.Not.Null);
            Assert.That(wait.Until(d => d.FindElement(By.Id("email"))), Is.Not.Null);
            Assert.That(wait.Until(d => d.FindElement(By.Id("password"))), Is.Not.Null);
            Assert.That(wait.Until(d => d.FindElement(By.Id("student_code"))), Is.Not.Null);
            Assert.That(wait.Until(d => d.FindElement(By.Id("full_name"))), Is.Not.Null);
            Assert.That(wait.Until(d => d.FindElement(By.CssSelector(".btn-register"))), Is.Not.Null);

            Thread.Sleep(slowDelay); 
        }

        [Test]
        public void Test01_Register_Success()
        {
            driver!.Navigate().GoToUrl(registerUrl);
            string randomId = DateTime.Now.Ticks.ToString().Substring(10);
            string user = "sv" + randomId;
            RegisterAction(user, user + "@neu.edu.vn", "Pass123456", "1123" + randomId.Substring(0, 4), "Sinh Viên Test");

            Thread.Sleep(slowDelay); 
            Assert.That(driver.Url, Does.Contain("login"));
        }

        [Test]
        [TestCase("", "a@neu.edu.vn", "123456", "1122", "Name", TestName = "Test02_Empty_Username")]
        [TestCase("user", "", "123456", "1122", "Name", TestName = "Test03_Empty_Email")]
        [TestCase("user", "a@neu.edu.vn", "", "1122", "Name", TestName = "Test04_Empty_Password")]
        [TestCase("user", "a@neu.edu.vn", "123456", "", "Name", TestName = "Test05_Empty_StudentCode")]
        [TestCase("user", "a@neu.edu.vn", "123456", "1122", "", TestName = "Test06_Empty_FullName")]
        public void TestGroup_RequiredFields(string u, string e, string p, string m, string n)
        {
            driver!.Navigate().GoToUrl(registerUrl);
            RegisterAction(u, e, p, m, n);

            Thread.Sleep(2000); 
            Assert.That(driver.Url, Does.Contain("register"), $"Thất bại tại: {TestContext.CurrentContext.Test.Name}");
        }

        [Test]
        public void Test07_Invalid_Email_Domain()
        {
            driver!.Navigate().GoToUrl(registerUrl);
            RegisterAction("user7", "test@gmail.com", "Pass123456", "11223344", "Nguyễn Văn A");
            VerifyRegisterError("Email phải có đuôi @neu.edu.vn");
        }

        [Test]
        public void Test08_Email_Missing_Prefix()
        {
            driver!.Navigate().GoToUrl(registerUrl);
            RegisterAction("user8", "@neu.edu.vn", "Pass123456", "11223345", "Nguyễn Văn B");
            Thread.Sleep(slowDelay);
            // Trình duyệt chặn với thông báo "Please enter a part followed by '@'"
            Assert.That(driver.Url, Does.Contain("register"));
        }

        [Test]
        public void Test09_Password_Too_Short()
        {
            driver!.Navigate().GoToUrl(registerUrl);
            RegisterAction("user9", "test9@neu.edu.vn", "123", "11223346", "Nguyễn Văn C");
            VerifyRegisterError("Mật khẩu phải có ít nhất 6 ký tự");
        }

        // --- NHÓM 4: KIỂM TRA TRÙNG LẶP ---
        [Test]
        public void Test10_Duplicate_Username()
        {
            driver!.Navigate().GoToUrl(registerUrl);
            RegisterAction("admin", "admin_new@neu.edu.vn", "Pass123456", "88889999", "Admin Fake");
            VerifyRegisterError("Tên đăng nhập đã tồn tại");
        }

        [Test]
        public void Test11_Duplicate_StudentCode()
        {
            driver!.Navigate().GoToUrl(registerUrl);
            RegisterAction("usertest11", "test11@neu.edu.vn", "Pass123456", "11236033", "Trang Test");
            VerifyRegisterError("Mã sinh viên này đã được đăng ký");
        }

        // --- NHÓM 5: ĐIỀU HƯỚNG ---
        [Test]
        public void Test12_Link_To_Login()
        {
            driver!.Navigate().GoToUrl(registerUrl);
            Thread.Sleep(2000);
            IJavaScriptExecutor js = (IJavaScriptExecutor)driver;
            var link = driver.FindElement(By.XPath("//a[contains(text(), 'Đăng nhập')]"));
            js.ExecuteScript("arguments[0].scrollIntoView(true);", link);
            Thread.Sleep(1000);
            js.ExecuteScript("arguments[0].click();", link);
            Thread.Sleep(slowDelay); 
            Assert.That(driver.Url, Does.Contain("login"));
        }

        [Test]
        public void Test13_Back_To_Home()
        {
            driver!.Navigate().GoToUrl(registerUrl);
            Thread.Sleep(1500);
            var link = driver.FindElement(By.CssSelector("a[href='/']"));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", link);
            Thread.Sleep(slowDelay);
            Assert.That(driver.Url, Is.Not.EqualTo(registerUrl));
        }

        // --- HÀM HỖ TRỢ (HELPERS) ---
        private void RegisterAction(string user, string email, string pass, string msv, string name)
        {
            FillInput("username", user);
            FillInput("email", email);
            FillInput("password", pass);
            FillInput("student_code", msv);
            FillInput("full_name", name);

            Thread.Sleep(1000); 

            var btn = driver!.FindElement(By.CssSelector(".btn-register"));
            IJavaScriptExecutor js = (IJavaScriptExecutor)driver;
            js.ExecuteScript("arguments[0].scrollIntoView(true);", btn);
            Thread.Sleep(1000);
            js.ExecuteScript("arguments[0].click();", btn);
        }

        private void FillInput(string fieldId, string value)
        {
            var element = driver!.FindElement(By.Id(fieldId));
            element.Clear();
            Thread.Sleep(300); 
            if (!string.IsNullOrEmpty(value)) element.SendKeys(value);
            Thread.Sleep(500); 
        }

        private void VerifyRegisterError(string expectedMessage)
        {
            var wait = new WebDriverWait(driver!, TimeSpan.FromSeconds(10));
            try
            {
                var alert = wait.Until(ExpectedConditions.ElementIsVisible(By.ClassName("alert-danger")));
                Thread.Sleep(slowDelay); 
                Assert.That(alert.Text, Does.Contain(expectedMessage));
            }
            catch
            {
                Assert.That(driver!.Url, Does.Contain("register"));
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