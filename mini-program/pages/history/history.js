const api = require('../../utils/api')
Page({
  data: { history: [], isEmpty: true, loading: false, page: 1, noMore: false },
  onShow() { this.setData({ page: 1, history: [], noMore: false }); this.loadHistory() },
  loadHistory() {
    if (this.data.loading || this.data.noMore) return
    this.setData({ loading: true })
    api.getHistory(this.data.page, 20).then(data => {
      const list = this.data.history.concat(data.list || [])
      this.setData({
        history: list,
        isEmpty: list.length === 0,
        loading: false,
        noMore: list.length >= data.total,
        page: this.data.page + 1
      })
    }).catch(() => { this.setData({ loading: false }) })
  },
  onReachBottom() { this.loadHistory() },
  onTapRecord(e) {
    const record = e.currentTarget.dataset.record
    wx.showModal({
      title: record.prediction,
      content: '置信度: ' + record.confidence + '%\n时间: ' + record.created_at,
      showCancel: false, confirmText: '知道了'
    })
  },
  onDeleteRecord(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认删除', content: '是否删除这条记录？',
      success: (res) => {
        if (res.confirm) {
          api.deleteHistory(id).then(() => {
            this.setData({ page: 1, history: [], noMore: false })
            this.loadHistory()
            wx.showToast({ title: '已删除', icon: 'success' })
          })
        }
      }
    })
  },
  onClearHistory() {
    wx.showModal({
      title: '确认清空', content: '是否清空所有识别历史记录？',
      success: (res) => {
        if (res.confirm) {
          api.clearHistory().then(() => {
            this.setData({ history: [], isEmpty: true })
            wx.showToast({ title: '已清空', icon: 'success' })
          })
        }
      }
    })
  }
})
