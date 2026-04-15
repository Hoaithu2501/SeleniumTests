using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.Support.UI;
using NUnit.Framework;
using SeleniumExtras.WaitHelpers;
using System;
using System.Linq;
using System.Threading;

namespace SeleniumTests
{
    [TestFixture]
    public class AdminClubManagementTests
    {
        private IWebDriver? driver;
        private WebDriverWait? wait;
        private string url = "http://127.0.0.1:5002";

        [SetUp]
        public void Setup()
        {
            var options = new ChromeOptions();
            options.AddArgument("--start-maximized");
            driver = new ChromeDriver(options);
            wait = new WebDriverWait(driver, TimeSpan.FromSeconds(30));
        }

        private void Login(string user, string pass)
        {
            driver!.Navigate().GoToUrl(url + "/login");
            var userInp = wait!.Until(ExpectedConditions.ElementIsVisible(By.Name("username")));
            userInp.Clear();
            userInp.SendKeys(user);
            driver.FindElement(By.Name("password")).SendKeys(pass);
            driver.FindElement(By.CssSelector("button[type='submit']")).Click();
            Thread.Sleep(2000);
        }

        // TC0: Kiểm tra giao diện trang quản lý CLB (UI/UX)
        [Test]
        public void Test_00_AdminClubs_UI_Check()
        {
            Login("admin", "admin123");
            driver!.Navigate().GoToUrl(url + "/admin/clubs");
            Assert.That(driver.Title, Does.Contain("Hệ thống"), "Tiêu đề trình duyệt không chứa từ khóa mong muốn!");
            var headerElement = wait!.Until(ExpectedConditions.ElementIsVisible(By.TagName("h3")));
            Assert.That(headerElement.Text, Does.Contain("Quản Lý Câu Lạc Bộ"), "Nội dung Header không đúng!");
            var searchInput = driver.FindElement(By.Id("searchInput"));
            Assert.That(searchInput.Displayed, Is.True, "Ô tìm kiếm không hiển thị!");
        }

        // TC1: Admin phê duyệt đơn thành lập CLB thành công
        [Test]
        public void Test_01_ApproveClub_Success()
        {
            Login("admin", "admin123");
            driver!.Navigate().GoToUrl(url + "/admin/clubs");
            var pendingRow = GetClubRowByStatus("Chờ duyệt");
            if (pendingRow == null) Assert.Ignore("Không tìm thấy CLB nào ở trạng thái 'Chờ duyệt'.");
            var approveBtn = pendingRow.FindElement(By.CssSelector("form input[value='approve'] + button"));
            ((IJavaScriptExecutor)driver!).ExecuteScript("arguments[0].click();", approveBtn);
            var alert = wait!.Until(ExpectedConditions.ElementIsVisible(By.ClassName("alert-success")));
            Assert.That(alert.Text, Does.Contain("Đã phê duyệt"), "Thông báo phê duyệt không hiển thị đúng!");
        }


        // TC2: Admin từ chối đơn thành lập CLB thành công
        [Test]
        public void Test_02_RejectClub_Success()
        {
            Login("admin", "admin123");
            driver!.Navigate().GoToUrl(url + "/admin/clubs");
            var pendingRow = GetClubRowByStatus("Chờ duyệt");
            if (pendingRow == null) Assert.Ignore("Không tìm thấy CLB nào ở trạng thái 'Chờ duyệt'.");
            var rejectBtn = pendingRow.FindElement(By.CssSelector("form input[value='reject'] + button"));
            ((IJavaScriptExecutor)driver!).ExecuteScript("arguments[0].click();", rejectBtn);
            var alert = wait!.Until(ExpectedConditions.ElementIsVisible(By.ClassName("alert-warning")));
            Assert.That(alert.Text, Does.Contain("Đã từ chối"), "Thông báo từ chối không hiển thị đúng!");
        }

        // TC3: Tìm kiếm CLB - Có kết quả
        [Test]
        public void Test_03_Search_FoundResults()
        {
            Login("admin", "admin123");
            driver!.Navigate().GoToUrl(url + "/admin/clubs");

            var searchInput = driver.FindElement(By.Id("searchInput"));
            string keyword = "CLB Talents";
            searchInput.Clear();
            foreach (char c in keyword) { searchInput.SendKeys(c.ToString()); Thread.Sleep(100); }

            Thread.Sleep(2000);
            var visibleRows = driver.FindElements(By.CssSelector(".club-row")).Where(r => r.Displayed).ToList();
            Assert.That(visibleRows.Count, Is.GreaterThan(0), "Tìm kiếm có kết quả nhưng không hiển thị hàng nào!");
        }

        // TC4: Tìm kiếm CLB - Không có kết quả
        [Test]
        public void Test_04_Search_NoResults()
        {
            Login("admin", "admin123");
            driver!.Navigate().GoToUrl(url + "/admin/clubs");

            var searchInput = driver.FindElement(By.Id("searchInput"));
            searchInput.Clear();
            searchInput.SendKeys("Kiem_Tra_Khong_Ton_Tai_123");

            Thread.Sleep(2000);
            var visibleRows = driver.FindElements(By.CssSelector(".club-row")).Where(r => r.Displayed).ToList();
            Assert.That(visibleRows.Count, Is.EqualTo(0), "Vẫn hiển thị kết quả dù từ khóa không tồn tại!");
        }

        private IWebElement? GetClubRowByStatus(string statusText)
        {
            var rows = driver!.FindElements(By.CssSelector(".club-row"));
            return rows.FirstOrDefault(r => r.Text.Contains(statusText));
        }

        [TearDown]
        public void TearDown()
        {
            if (driver != null) { driver.Quit(); driver.Dispose(); }
        }
    }
}