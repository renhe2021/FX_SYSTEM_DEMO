// app.js
App({
  globalData: {
    apiBaseUrl: 'http://localhost:5000/api',  // 开发环境
    // apiBaseUrl: 'https://your-domain.com/api',  // 生产环境
    userInfo: null
  },

  onLaunch() {
    console.log('BMAD量化系统启动');
  },

  // 封装API请求
  request(options) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: this.globalData.apiBaseUrl + options.url,
        method: options.method || 'GET',
        data: options.data || {},
        header: {
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (res.data.success) {
            resolve(res.data);
          } else {
            reject(res.data.error || '请求失败');
          }
        },
        fail: (err) => {
          reject(err);
        }
      });
    });
  },

  // 获取策略列表
  getStrategies() {
    return this.request({ url: '/strategies' });
  },

  // 获取回测列表
  getBacktests(params = {}) {
    let url = '/backtests';
    const query = [];
    if (params.strategy) query.push(`strategy=${params.strategy}`);
    if (params.symbol) query.push(`symbol=${params.symbol}`);
    if (params.limit) query.push(`limit=${params.limit}`);
    if (query.length > 0) url += '?' + query.join('&');
    return this.request({ url });
  },

  // 获取回测详情
  getBacktestDetail(id) {
    return this.request({ url: `/backtests/${id}` });
  },

  // 运行回测
  runBacktest(strategyId, options = {}) {
    return this.request({
      url: '/backtests/run',
      method: 'POST',
      data: {
        strategy_id: strategyId,
        ...options
      }
    });
  },

  // 获取统计信息
  getStatistics() {
    return this.request({ url: '/backtests/statistics' });
  }
});
