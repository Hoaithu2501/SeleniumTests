#nullable disable
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
    public class FullMembershipProcessTests
    {
        private IWebDriver driver;
        private WebDriverWait wait;
        private string baseUrl = "http://127.0.0.1:5002";

        [SetUp]
        public void Setup()
        {
            var options = new ChromeOptions();
            options.AddArgument("--start-maximized");
            driver = new ChromeDriver(options);
            wait = new WebDriverWait(driver, TimeSpan.FromSeconds(20));
        }
        // [TC0]: KIỂM TRA GIAO DIỆN
        [Test]
        public void TC0_ClubApplications_UI_Check()
        {
            Login("talents", "123456");
            driver.Navigate().GoToUrl(baseUrl + "/club/applications");
            Assert.That(driver.Title, Does.Contain("Hệ thống"), "Title sai!");
            var pageTitle = wait.Until(ExpectedConditions.ElementIsVisible(By.CssSelector(".page-title"))).Text;
            Assert.That(pageTitle, Does.Contain("Đơn Đăng Ký Gia Nhập"));
            Assert.That(driver.FindElement(By.TagName("thead")).Text, Does.Contain("Sinh Viên"));
        }

        // [TC1]: QUY TRÌNH DUYỆT ĐƠN THÀNH CÔNG
        [Test]
        public void TC1_StudentApply_ClubApprove_Success()
        {
            Login("lan1", "123456");
            ApplyToClub("CLB Talents");
            Logout();
            Login("talents", "123456");
            ProcessFirstApplication("approve");
            var alert = wait.Until(ExpectedConditions.ElementIsVisible(By.CssSelector(".alert-success")));
            Assert.That(alert.Text, Does.Contain("Đã duyệt đơn đăng ký tham gia"));
        }

        // [TC2]: TỪ CHỐI ĐƠN NHƯNG BẤM "HỦY" (CANCEL) -> KHÔNG THAY ĐỔI
        [Test]
        public void TC2_StudentApply_ClubReject_Cancel()
        {
            Login("lan2", "123456");
            ApplyToClub("CLB Talents");
            Logout();
            Login("talents", "123456");
            driver.Navigate().GoToUrl(baseUrl + "/club/applications");
            Thread.Sleep(3000);
            var rejectBtn = wait.Until(ExpectedConditions.ElementToBeClickable(
                By.XPath("//button[contains(@class, 'btn-outline-danger') and contains(., 'Từ chối')]")));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", rejectBtn);
            Thread.Sleep(1000);
            wait.Until(ExpectedConditions.AlertIsPresent()).Dismiss();
            Thread.Sleep(3000);
            var statusBadge = driver.FindElement(By.CssSelector(".badge.bg-warning"));
            Assert.That(statusBadge.Text, Does.Contain("Đang chờ duyệt"));
        }

        // [TC3]: QUY TRÌNH TỪ CHỐI ĐƠN THÀNH CÔNG (BẤM OK)
        [Test]
        public void TC3_StudentApply_ClubReject_Success()
        {
            Login("lan3", "123456");
            ApplyToClub("CLB Talents");
            Logout();

            Login("talents", "123456");
            ProcessFirstApplication("reject");

            var alert = wait.Until(ExpectedConditions.ElementIsVisible(By.CssSelector(".alert")));
            Assert.That(alert.Text, Does.Contain("Đã từ chối đơn đăng ký"));
        }

        private void Login(string user, string pass)
        {
            driver.Navigate().GoToUrl(baseUrl + "/login");
            wait.Until(ExpectedConditions.ElementIsVisible(By.Name("username"))).Clear();
            driver.FindElement(By.Name("username")).SendKeys(user);
            driver.FindElement(By.Name("password")).SendKeys(pass);
            driver.FindElement(By.CssSelector("button[type='submit']")).Click();
            Thread.Sleep(3000);
        }

        private void Logout()
        {
            driver.Navigate().GoToUrl(baseUrl + "/logout");
            Thread.Sleep(3000);
        }

        private void ApplyToClub(string clubName)
        {
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            Thread.Sleep(3000);

            string cardXpath = $"//h6[normalize-space()='{clubName}']/ancestor::div[contains(@class, 'card')]";

            try
            {
                var applyBtn = wait.Until(ExpectedConditions.ElementToBeClickable(By.XPath(cardXpath + "//button[.//i[contains(@class, 'fa-plus')]]")));
                ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", applyBtn);

                var modal = wait.Until(ExpectedConditions.ElementIsVisible(By.CssSelector(".modal.show")));
                Thread.Sleep(1000);

                var motivationField = modal.FindElement(By.Name("motivation"));
                string lyDo = "Lý do tự động TC: " + DateTime.Now.ToString("HH:mm:ss");
                ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].value = arguments[1];", motivationField, lyDo);
                ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", motivationField);

                Thread.Sleep(1000);

                var submitBtn = modal.FindElement(By.XPath(".//button[contains(., 'Gửi Đơn Ngay')]"));
                submitBtn.Click();

                wait.Until(ExpectedConditions.ElementIsVisible(By.CssSelector(".alert-success")));
                Thread.Sleep(3000);
            }
            catch (Exception ex)
            {
                Console.WriteLine("Lỗi ở ApplyToClub: " + ex.Message);
                throw;
            }
        }

        private void ProcessFirstApplication(string action)
        {
            driver.Navigate().GoToUrl(baseUrl + "/club/applications");
            Thread.Sleep(3000);

            if (action == "approve")
            {
                var btn = wait.Until(ExpectedConditions.ElementToBeClickable(By.XPath("//button[contains(@class, 'btn-success') and contains(., 'Duyệt')]")));
                ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", btn);
            }
            else
            {
                var btn = wait.Until(ExpectedConditions.ElementToBeClickable(By.XPath("//button[contains(@class, 'btn-outline-danger') and contains(., 'Từ chối')]")));
                ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", btn);

                Thread.Sleep(2000);
                wait.Until(ExpectedConditions.AlertIsPresent()).Accept();
            }
            Thread.Sleep(3000);
        }

        [TearDown]
        public void TearDown()
        {
            if (driver != null)
            {
                driver.Quit();
                driver.Dispose();
            }
        }
    }
}
