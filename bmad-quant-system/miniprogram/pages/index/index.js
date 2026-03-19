// pages/index/index.js
const app = getApp();

Page({
  data: {
    statistics: {
      total_backtests: 0,
      strategies: [],
      strategy_stats: []
    },
    recentBacktests: [],
    loading: true
  },

  onLoad() {
    this.loadData();
  },

  onShow() {
    this.loadData();
  },

  onPullDownRefresh() {
    this.loadData().then(() => {
      wx.stopPullDownRefresh();
    });
  },

  async loadData() {
    try {
      // 获取统计信息
      const statsRes = await app.getStatistics();
      this.setData({
        statistics: statsRes.data
      });

      // 获取最近回测
      const backtestsRes = await app.getBacktests({ limit: 5 });
      this.setData({
        recentBacktests: backtestsRes.data.map(item => ({
          ...item,
          created_at: this.formatDate(item.created_at)
        })),
        loading: false
      });
    } catch (err) {
      console.error('加载数据失败:', err);
      this.setData({ loading: false });
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
    }
  },

  formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
  },

  goToStrategies() {
    wx.switchTab({
      url: '/pages/strategies/strategies'
    });
  },

  goToReport(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/report/report?id=${id}`
    });
  }
});
