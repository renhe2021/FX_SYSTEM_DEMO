const app = getApp()

Page({
  data: {
    backtest: {},
    trades: []
  },

  onLoad(options) {
    if (options.id) {
      this.loadBacktestDetail(options.id)
    }
  },

  loadBacktestDetail(id) {
    wx.showLoading({ title: '加载中...' })
    
    wx.request({
      url: `${app.globalData.apiBase}/api/backtests/${id}`,
      success: (res) => {
        if (res.data.success) {
          const data = res.data.data
          this.setData({
            backtest: {
              backtest_id: data.backtest_id,
              strategy_name: data.strategy_name,
              created_at: this.formatDate(data.created_at),
              total_return: (data.metrics.total_return * 100).toFixed(2),
              sharpe_ratio: data.metrics.sharpe_ratio.toFixed(2),
              max_drawdown: (data.metrics.max_drawdown * 100).toFixed(2),
              win_rate: (data.metrics.win_rate * 100).toFixed(1),
              initial_capital: this.formatNumber(data.metrics.initial_capital),
              final_capital: this.formatNumber(data.metrics.final_capital),
              total_pnl: this.formatNumber(data.metrics.total_pnl),
              total_trades: data.metrics.total_trades,
              winning_trades: data.metrics.winning_trades,
              losing_trades: data.metrics.losing_trades,
              avg_win: this.formatNumber(data.metrics.avg_win || 0),
              avg_loss: this.formatNumber(data.metrics.avg_loss || 0),
              profit_factor: (data.metrics.profit_factor || 0).toFixed(2),
              annual_return: ((data.metrics.annual_return || 0) * 100).toFixed(2),
              annual_volatility: ((data.metrics.annual_volatility || 0) * 100).toFixed(2),
              calmar_ratio: (data.metrics.calmar_ratio || 0).toFixed(2)
            },
            trades: (data.trades || []).slice(0, 50).map(t => ({
              date: t.date,
              action: t.action,
              symbol: t.symbol,
              price: t.price.toFixed(4),
              pnl: t.pnl ? t.pnl.toFixed(2) : '0.00'
            }))
          })
          
          this.drawEquityChart(data.equity_curve || [])
          this.drawMonthlyChart(data.monthly_returns || [])
        }
      },
      fail: () => {
        wx.showToast({ title: '加载失败', icon: 'none' })
      },
      complete: () => {
        wx.hideLoading()
      }
    })
  },

  formatDate(dateStr) {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
  },

  formatNumber(num) {
    if (num === undefined || num === null) return '0'
    return Number(num).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  },

  drawEquityChart(equityCurve) {
    if (!equityCurve || equityCurve.length === 0) return
    
    const ctx = wx.createCanvasContext('equityChart')
    const width = 690
    const height = 380
    const padding = 40
    
    const values = equityCurve.map(e => e.value)
    const minVal = Math.min(...values)
    const maxVal = Math.max(...values)
    const range = maxVal - minVal || 1
    
    // 绘制网格
    ctx.setStrokeStyle('#f0f0f0')
    ctx.setLineWidth(1)
    for (let i = 0; i <= 4; i++) {
      const y = padding + (height - 2 * padding) * i / 4
      ctx.beginPath()
      ctx.moveTo(padding, y)
      ctx.lineTo(width - padding, y)
      ctx.stroke()
    }
    
    // 绘制曲线
    ctx.setStrokeStyle('#667eea')
    ctx.setLineWidth(2)
    ctx.beginPath()
    
    equityCurve.forEach((point, i) => {
      const x = padding + (width - 2 * padding) * i / (equityCurve.length - 1)
      const y = height - padding - (height - 2 * padding) * (point.value - minVal) / range
      
      if (i === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()
    
    // 填充渐变
    ctx.setFillStyle('rgba(102, 126, 234, 0.1)')
    ctx.lineTo(width - padding, height - padding)
    ctx.lineTo(padding, height - padding)
    ctx.closePath()
    ctx.fill()
    
    ctx.draw()
  },

  drawMonthlyChart(monthlyReturns) {
    if (!monthlyReturns || monthlyReturns.length === 0) return
    
    const ctx = wx.createCanvasContext('monthlyChart')
    const width = 690
    const height = 380
    const padding = 40
    
    const values = monthlyReturns.map(m => m.return)
    const maxAbs = Math.max(...values.map(Math.abs)) || 0.1
    
    const barWidth = (width - 2 * padding) / monthlyReturns.length * 0.7
    const gap = (width - 2 * padding) / monthlyReturns.length * 0.3
    const zeroY = height / 2
    
    // 绘制零线
    ctx.setStrokeStyle('#ddd')
    ctx.setLineWidth(1)
    ctx.beginPath()
    ctx.moveTo(padding, zeroY)
    ctx.lineTo(width - padding, zeroY)
    ctx.stroke()
    
    // 绘制柱状图
    monthlyReturns.forEach((item, i) => {
      const x = padding + i * (barWidth + gap) + gap / 2
      const barHeight = (height / 2 - padding) * Math.abs(item.return) / maxAbs
      
      if (item.return >= 0) {
        ctx.setFillStyle('#10b981')
        ctx.fillRect(x, zeroY - barHeight, barWidth, barHeight)
      } else {
        ctx.setFillStyle('#ef4444')
        ctx.fillRect(x, zeroY, barWidth, barHeight)
      }
    })
    
    ctx.draw()
  },

  exportReport() {
    wx.showToast({ title: '报告已导出', icon: 'success' })
  },

  onShareAppMessage() {
    return {
      title: `${this.data.backtest.strategy_name} 回测报告`,
      path: `/pages/detail/detail?id=${this.data.backtest.backtest_id}`
    }
  }
})
