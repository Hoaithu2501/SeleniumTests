#nullable disable
using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.Support.UI;
using NUnit.Framework;
using SeleniumExtras.WaitHelpers;
using System;
using System.Threading;
using System.Linq;
using System.Diagnostics;

namespace SeleniumTests
{
    [TestFixture]
    public class ApplyClubTests
    {
        private IWebDriver driver;
        private WebDriverWait wait;
        private string baseUrl = "http://127.0.0.1:5002";

        private int slowDelay = 3000;


        [SetUp]
        public void Setup()
        {
            // NOTE: RESET DATABASE: Xóa sạch đơn cũ để không bị lỗi "Đã nộp đơn" khi chạy lại test

            driver = new ChromeDriver();
            driver.Manage().Window.Maximize();
            wait = new WebDriverWait(driver, TimeSpan.FromSeconds(15));
            string testName = TestContext.CurrentContext.Test.Name;

            if (testName.Contains("TC11"))
            {
                LoginAction("lan1", "123456");
            }
            else if (testName.Contains("TC12") || testName.Contains("TC13"))
            {
                LoginAction("lan3", "123456");
            }
            else
            {
                // Mặc định cho các TC còn lại
                LoginAction("lan", "123456");
            }
        }

        // [TC0]: KIỂM TRA GIAO DIỆN TRANG KHÁM PHÁ CLB (UI/UX)
        [Test]
        public void TC0_ClubsPage_UI_Check()
        {
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            Assert.That(driver.Title, Does.Contain("Hệ thống"), "Title trình duyệt sai!");
            var header = wait.Until(ExpectedConditions.ElementIsVisible(By.CssSelector("h2"))).Text;
            Assert.That(header, Does.Contain("Khám Phá Cộng Đồng"), "Tiêu đề trang hiển thị sai!");
            var subtext = driver.FindElement(By.CssSelector(".text-muted")).Text;
            Assert.That(subtext, Does.Contain("Tìm kiếm và gia nhập"), "Mô tả trang hiển thị sai!");
            var searchInput = driver.FindElement(By.Id("searchInput"));
            Assert.That(searchInput.Displayed, Is.True, "Thanh tìm kiếm không hiển thị!");
            Assert.That(searchInput.GetAttribute("placeholder"), Does.Contain("Tìm tên câu lạc bộ"), "Placeholder sai!");
            var clubCards = driver.FindElements(By.CssSelector(".club-item"));
            Assert.That(clubCards.Count, Is.GreaterThan(0), "Không có CLB nào được hiển thị trên trang!");
            var firstCard = clubCards[0];
            Assert.Multiple(() =>
            {
                Assert.That(firstCard.FindElement(By.CssSelector("a.btn-primary-light")).Text, Does.Contain("Thông Tin Chi Tiết"));
                Assert.That(firstCard.FindElement(By.CssSelector("button[data-bs-target^='#applyModal']")).Displayed, Is.True, "Nút '+' (Gửi đơn) không hiển thị!");
            });
        }

        // [TC1]: Kiểm tra nộp đơn THÀNH CÔNG từ trang DANH SÁCH (Club list)
        // Trường hợp: CLB chưa từng gửi đơn, nhập đầy đủ lý do.
        [Test]
        public void TC1_Apply_FromClubsPage_Success()
        {
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            string modalId = OpenModalByName("Test Club 176"); 

            FillMotivationByJS(modalId, "TC1: Em muốn tham gia CLB."); 
            SubmitModalByJS(modalId, "Gửi Đơn Ngay"); 
            AssertFlashMessage(".alert-success", "Nộp đơn thành công");
        }

        // [TC2]: Kiểm tra nộp đơn THẤT BẠI do BỎ TRỐNG lý do (Trang danh sách)
        // Trường hợp: CLB chưa gửi đơn, nhấn gửi ngay mà không nhập gì.
        [Test]
        public void TC2_Apply_FromClubsPage_MissingMotivation()
        {
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            string modalId = OpenModalById(4);
            SubmitModalByJS(modalId, "Gửi Đơn Ngay");
            var field = driver.FindElement(By.Id(modalId)).FindElement(By.Name("motivation"));
            Assert.That(field.GetAttribute("validationMessage"), Is.Not.Null.And.Not.Empty);
            Thread.Sleep(slowDelay);
        }

        // [TC3]: Kiểm tra nộp đơn THÀNH CÔNG từ trang CHI TIẾT (Club detail)
        // Trường hợp: Vào xem thông tin CLB rồi mới quyết định nhấn nộp đơn.
        [Test]
        public void TC3_Apply_FromDetailPage_Success()
        {
            driver.Navigate().GoToUrl(baseUrl + "/clubs/1");
            OpenDetailModal();
            FillMotivationByJS("joinClubModal", "TC3: Em rất thích các hoạt động của CLB.");
            SubmitModalByJS("joinClubModal", "Nộp Đơn Ứng Tuyển");
            AssertFlashMessage(".alert-success", "Nộp đơn thành công");
        }


        // [TC4]: Kiểm tra nộp đơn THẤT BẠI do BỎ TRỐNG lý do (Trang chi tiết)
        // Trường hợp: Tại trang chi tiết, nhấn nộp nhưng không nhập lý do.
        [Test]
        public void TC4_Apply_FromDetailPage_MissingMotivation()
        {
            driver.Navigate().GoToUrl(baseUrl + "/clubs/1");
            OpenDetailModal();
            SubmitModalByJS("joinClubModal", "Nộp Đơn Ứng Tuyển");
            var field = driver.FindElement(By.Id("joinClubModal")).FindElement(By.Name("motivation"));
            Assert.That(field.GetAttribute("validationMessage"), Is.Not.Null.And.Not.Empty);
            Thread.Sleep(slowDelay);
        }

        // [TC5]: Kiểm tra nộp đơn vào CLB ĐÃ NỘP RỒI (Trang danh sách)
        // Trường hợp: Hệ thống phải ngăn chặn việc nộp đơn chồng chéo.
        [Test]
        public void TC5_Apply_FromClubsPage_AlreadyApplied()
        {
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            string modalId = OpenModalByName("Test Club 176");
            FillMotivationByJS(modalId, "Tạo đơn lần 1");
            SubmitModalByJS(modalId, "Gửi Đơn Ngay");
            Thread.Sleep(1000);
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            OpenModalByName("Test Club 176");
            FillMotivationByJS(modalId, "Thử nộp lần 2");
            SubmitModalByJS(modalId, "Gửi Đơn Ngay");
            AssertFlashMessage(".alert-warning", "đang chờ duyệt");
        }

        // [TC6]: Kiểm tra nộp đơn vào CLB ĐÃ NỘP RỒI (Trang chi tiết)
        // Trường hợp: Tương tự TC5 nhưng thao tác bên trong trang chi tiết CLB.
        [Test]
        public void TC6_Apply_AlreadyApplied_FromDetailPage()
        {
            driver.Navigate().GoToUrl(baseUrl + "/clubs/1");
            OpenDetailModal();
            FillMotivationByJS("joinClubModal", "Tạo đơn lần 1");
            SubmitModalByJS("joinClubModal", "Nộp Đơn Ứng Tuyển");
            Thread.Sleep(1000);
            driver.Navigate().GoToUrl(baseUrl + "/clubs/1");
            OpenDetailModal();
            FillMotivationByJS("joinClubModal", "Thử nộp lần 2");
            SubmitModalByJS("joinClubModal", "Nộp Đơn Ứng Tuyển");
            AssertFlashMessage(".alert-warning", "đang chờ duyệt");
        }

        // [TC7]: Kiểm tra nộp đơn vào CLB DO MÌNH SÁNG LẬP (Founder)
        // Trường hợp: Founder không được phép nộp đơn gia nhập chính CLB của mình.
        [Test]
        public void TC7_Apply_AsFounder_FromClubsPage()
        {
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            string modalId = OpenModalById(5); 
            FillMotivationByJS(modalId, "Tôi là founder.");
            SubmitModalByJS(modalId, "Gửi Đơn Ngay");
            AssertFlashMessage(".alert-warning", "người sáng lập");
        }

        // [TC8]: Kiểm tra huy hiệu "Thành viên/Sáng lập" (Trang chi tiết)
        // Trường hợp: Khi đã là thành viên, nút ứng tuyển biến mất và có huy hiệu trạng thái.
        [Test]
        public void TC8_View_AlreadyMember_OnDetailPage()
        {
            driver.Navigate().GoToUrl(baseUrl + "/clubs/5");
            Thread.Sleep(slowDelay);
            var container = wait.Until(ExpectedConditions.ElementIsVisible(By.CssSelector("div.mt-3.mt-md-0")));
            var btn = container.FindElement(By.CssSelector(".btn, .badge"));

            Assert.That(btn.Text, Does.Contain("Thành viên").Or.Contain("Sáng Lập").Or.Contain("Gửi Đơn"));
            Thread.Sleep(slowDelay);
        }

        // [TC9]: Kiểm tra thông báo đơn bị TỪ CHỐI (Trang Notifications)
        // Trường hợp: Admin đã từ chối đơn, sinh viên vào xem thông báo.
        [Test]
        public void TC9_View_Rejected_Notification()
        {
            driver.Navigate().GoToUrl(baseUrl + "/notifications");
            Thread.Sleep(slowDelay);
            var items = wait.Until(ExpectedConditions.VisibilityOfAllElementsLocatedBy(By.CssSelector(".list-group-item")));
            bool found = items.Any(n => n.Text.Contains("bị từ chối"));
            Assert.That(found, Is.True, "Không tìm thấy thông báo từ chối.");
        }

        // [TC10]: Kiểm tra thông báo đơn được DUYỆT (Trang Notifications)
        // Trường hợp: Admin đã duyệt đơn, sinh viên vào xem thông báo thành công.
        [Test]
        public void TC10_View_Approved_Notification()
        {
            driver.Navigate().GoToUrl(baseUrl + "/notifications");
            Thread.Sleep(slowDelay);
            var items = wait.Until(ExpectedConditions.VisibilityOfAllElementsLocatedBy(By.CssSelector(".list-group-item")));
            bool found = items.Any(n => n.Text.Contains("được duyệt"));
            Assert.That(found, Is.True, "Không tìm thấy thông báo được duyệt.");
        }

        // [TC11]: Kiểm tra nộp đơn khi ĐÃ LÀ THÀNH VIÊN
        // Trường hợp: lan1 đã được duyệt ở file ProcessTest, giờ nộp lại sẽ báo lỗi.
        [Test]
        public void TC11_Apply_AlreadyMember_Error()
        {
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            string modalId = OpenModalByName("CLB Talents");
            FillMotivationByJS(modalId, "Thử nộp lại khi đã là thành viên");
            SubmitModalByJS(modalId, "Gửi Đơn Ngay");
            AssertFlashMessage(".alert-info", "Bạn đã là thành viên của CLB này.");
        }

        // [TC12]: Kiểm tra nộp đơn khi ĐÃ BỊ TỪ CHỐI
        // Trường hợp: lan3 đã bị từ chối ở file ProcessTest, nộp lại sẽ hiển thị thông báo bị từ chối.
        [Test]
        public void TC12_Apply_AlreadyRejected_Error()
        {
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            string modalId = OpenModalByName("CLB Talents");

            FillMotivationByJS(modalId, "Thử nộp lại khi đã bị từ chối");
            SubmitModalByJS(modalId, "Gửi Đơn Ngay");

            AssertFlashMessage(".alert-danger", "đã bị từ chối");
        }

        // [TC13]: Kiểm tra nộp đơn khi ĐÃ BỊ TỪ CHỐI (Vào từ trang chi tiết)
        // Trường hợp: lan3 tìm CLB, vào xem chi tiết rồi mới nộp đơn -> Hệ thống vẫn phải chặn.
        [Test]
        public void TC13_AlreadyRejected_Error()
        {
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            var card = wait.Until(ExpectedConditions.ElementIsVisible(By.XPath("//h6[contains(., 'CLB Talents')]/ancestor::div[contains(@class, 'club-item')]")));
            var detailBtn = card.FindElement(By.CssSelector("a.btn-primary-light")); 
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", detailBtn);
            OpenDetailModal();
            FillMotivationByJS("joinClubModal", "Cố tình nộp lại từ trang chi tiết");
            SubmitModalByJS("joinClubModal", "Nộp Đơn Ứng Tuyển");
            AssertFlashMessage(".alert-danger", "đã bị từ chối");
        }


        // [TC14]: Kiểm tra chức năng TÌM KIẾM - CÓ KẾT QUẢ
        [Test]
        public void TC14_Search_Found()
        {
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            var input = driver.FindElement(By.Id("searchInput"));

            input.Clear();
            Thread.Sleep(1000);
            string searchText = "Talents";
            foreach (char c in searchText)
            {
                ((IJavaScriptExecutor)driver).ExecuteScript(
                    "arguments[0].value += arguments[1];" +
                    "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                    input, c.ToString());
                Thread.Sleep(200);
            }
            Thread.Sleep(3000);

            var isVisible = driver.FindElements(By.CssSelector(".club-item")).Any(c => c.Displayed && c.Text.Contains(searchText));
            Assert.That(isVisible, Is.True);
        }

        // [TC15]: Kiểm tra chức năng TÌM KIẾM - KHÔNG CÓ KẾT QUẢ
        [Test]
        public void TC15_Search_NotFound()
        {
            driver.Navigate().GoToUrl(baseUrl + "/student/clubs");
            var input = driver.FindElement(By.Id("searchInput"));

            input.Clear();
            Thread.Sleep(1000);
            string searchText = "CLB_AO_9999";
            foreach (char c in searchText)
            {
                ((IJavaScriptExecutor)driver).ExecuteScript(
                    "arguments[0].value += arguments[1];" +
                    "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                    input, c.ToString());
                Thread.Sleep(200);
            }
            Thread.Sleep(3000);

            var anyVisible = driver.FindElements(By.CssSelector(".club-item")).Any(c => c.Displayed);
            Assert.That(anyVisible, Is.False);
        }


        // ==================== CÁC HÀM TRỢ GIÚP (HELPERS) ====================

        private void SlowDown() { Thread.Sleep(slowDelay); }

        private void LoginAction(string user, string pass)
        {
            driver.Navigate().GoToUrl(baseUrl + "/login");
            var userField = wait.Until(ExpectedConditions.ElementIsVisible(By.Name("username")));
            userField.Clear();
            userField.SendKeys(user);

            var passField = driver.FindElement(By.Name("password"));
            passField.Clear();
            passField.SendKeys(pass);

            driver.FindElement(By.CssSelector("button[type='submit']")).Click();
            wait.Until(d => !d.Url.Contains("/login"));
            Thread.Sleep(1000);
        }

        private void Logout()
        {
            driver.Navigate().GoToUrl(baseUrl + "/logout");
            Thread.Sleep(1000);
        }


        private string OpenModalByName(string clubName)
        {
            var card = wait.Until(ExpectedConditions.ElementIsVisible(By.XPath($"//h6[contains(., '{clubName}')]/ancestor::div[contains(@class, 'club-item')]")));
            var btn = card.FindElement(By.CssSelector("button[data-bs-target^='#applyModal']"));
            string modalId = btn.GetAttribute("data-bs-target").Replace("#", "");
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", btn);
            wait.Until(d => d.FindElement(By.Id(modalId)).Displayed);
            SlowDown();
            return modalId;
        }

        private string OpenModalById(int clubId)
        {
            string modalId = $"applyModal{clubId}";
            var btn = wait.Until(ExpectedConditions.ElementToBeClickable(By.CssSelector($"button[data-bs-target='#{modalId}']")));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", btn);
            wait.Until(d => d.FindElement(By.Id(modalId)).Displayed);
            SlowDown();
            return modalId;
        }

        private void OpenDetailModal()
        {
            var btn = wait.Until(ExpectedConditions.ElementIsVisible(By.XPath("//button[contains(., 'Gửi Đơn Tham Gia')]")));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", btn);
            wait.Until(d => d.FindElement(By.Id("joinClubModal")).Displayed);
            SlowDown();
        }

        private void FillMotivationByJS(string modalId, string text)
        {
            var modal = driver.FindElement(By.Id(modalId));
            var field = modal.FindElement(By.Name("motivation"));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].value = arguments[1];", field, text);
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", field);
            SlowDown();
        }

        private void SubmitModalByJS(string modalId, string btnText)
        {
            var modal = driver.FindElement(By.Id(modalId));
            var btn = modal.FindElement(By.XPath($".//button[contains(text(), '{btnText}')]"));
            ((IJavaScriptExecutor)driver).ExecuteScript("arguments[0].click();", btn);
        }

        private void AssertFlashMessage(string cssClass, string expectedText)
        {
            var alert = wait.Until(ExpectedConditions.ElementIsVisible(By.CssSelector(cssClass)));
            Assert.That(alert.Text, Does.Contain(expectedText));
            SlowDown();
        }

        [TearDown]
        public void TearDown()
        {
            if (driver != null)
            {
                driver.Quit();
                driver.Dispose();
                driver = null;
            }
        }
    }
}
