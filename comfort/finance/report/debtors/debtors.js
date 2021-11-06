frappe.query_reports["Debtors"] = {
  onload(report) {
    report.$message.remove();
    report.$summary
      .css("justify-content", "center")
      .css("padding", "var(--padding-2xl)");

    // Patch report.render_summary to set appropriate margin (for 4 items)
    let old_func = report.render_summary;
    report.render_summary = (data) => {
      old_func.call(report, data);
      $(".summary-item").css("margin", "0px");
    };
  },
};
