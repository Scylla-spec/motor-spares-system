import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class SalesTrendChart(FigureCanvasQTAgg):
    """Embedded line chart showing daily revenue across a month (FR-22).

    Backed entirely by managers.reports_manager.get_monthly_sales_summary(),
    which already returns a day-by-day revenue breakdown \u2014 this widget
    just visualizes that data, no new queries involved.
    """
    def __init__(self, parent=None):
        self.figure = Figure(figsize=(6, 2.6), tight_layout=True)
        super().__init__(self.figure)
        if parent is not None:
            self.setParent(parent)
        self.ax = self.figure.add_subplot(111)
        self._draw_empty()

    def _draw_empty(self):
        self.ax.clear()
        self.ax.text(
            0.5, 0.5, "Run a monthly report to see the sales trend",
            ha="center", va="center", transform=self.ax.transAxes, color="#888888"
        )
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.draw()

    def update_chart(self, rows, month_label: str):
        """rows: list of dicts with 'date' and 'total_revenue' keys, as
        returned by managers.reports_manager.get_monthly_sales_summary().
        """
        self.ax.clear()

        if not rows:
            self._draw_empty()
            return

        day_labels = [r["date"][-2:] for r in rows]  # e.g. '01', '02', ... for compact x-axis labels
        revenue = [r["total_revenue"] for r in rows]
        x = list(range(len(day_labels)))

        self.ax.plot(x, revenue, marker="o", markersize=3, linewidth=1.5, color="#2980b9")
        self.ax.fill_between(x, revenue, alpha=0.10, color="#2980b9")

        self.ax.set_title(f"Daily Revenue \u2014 {month_label}", fontsize=10)
        self.ax.set_xlabel("Day of Month", fontsize=8)
        self.ax.set_ylabel("Revenue ($)", fontsize=8)
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(day_labels, fontsize=7)
        self.ax.tick_params(axis='y', labelsize=7)

        # Thin out x labels on long months so they don't overlap
        if len(x) > 15:
            for i, label in enumerate(self.ax.get_xticklabels()):
                if i % 3 != 0:
                    label.set_visible(False)

        self.ax.grid(True, linestyle="--", alpha=0.35)
        self.draw()
