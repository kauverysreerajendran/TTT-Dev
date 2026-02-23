document.addEventListener("DOMContentLoaded", function () {
  const reportForm = document.getElementById("reportForm");
  if (reportForm) {
    reportForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const module = document.getElementById("module").value;
      const successMessage = document.getElementById("successMessage");

      if (!module) {
        alert("Please select a module");
        return;
      }

      // Hide success message
      successMessage.style.display = "none";

      // Use Fetch API to download without page navigation/loading
      const downloadUrl = this.action + "?module=" + encodeURIComponent(module);

      fetch(downloadUrl)
        .then((response) => {
          if (!response.ok) throw new Error("Download failed");
          return response.blob();
        })
        .then((blob) => {
          // Create blob download without page navigation
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = module + "_report.xlsx";
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);

          // Show success message immediately after download
          successMessage.style.display = "block";
        })
        .catch((error) => {
          console.error("Error downloading file:", error);
          alert("Failed to download report. Please try again.");
        });
    });
  }
});
