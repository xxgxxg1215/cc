const api = require('../../utils/api')
const app = getApp()
Page({
    data: {
        userInfo: null,
        isLoggedIn: false,
        historyCount: 0
    },
    onShow() {
        const userInfo = app.globalData.userInfo
        if (userInfo) {
            this.setData({ userInfo, isLoggedIn: true })
            // 获取历史记录条数
            api.getHistory(1, 1).then(data => {
                this.setData({ historyCount: data.total || 0 })
            }).catch(() => { })
        }
    },
    onLogin() {
        app.login((data) => {
            this.setData({ userInfo: data.user, isLoggedIn: true })
        })
    },
    onLogout() {
        wx.showModal({
            title: '退出登录', content: '确定要退出登录吗？',
            success: (res) => {
                if (res.confirm) {
                    app.globalData.token = ''
                    app.globalData.userInfo = null
                    wx.removeStorageSync('token')
                    wx.removeStorageSync('userInfo')
                    this.setData({ userInfo: null, isLoggedIn: false, historyCount: 0 })
                    wx.showToast({ title: '已退出', icon: 'success' })
                }
            }
        })
    },
    onGoHistory() { wx.navigateTo({ url: '/pages/history/history' }) }
})
