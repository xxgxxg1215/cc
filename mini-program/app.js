App({
  globalData: {
    apiBase: 'http://localhost:8000',
    token: '',
    userInfo: null
  },

  onLaunch() {
    // 尝试从缓存恢复登录态
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    if (token) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
    }
  },

  /**
   * 登录（静默 or 用户触发）
   */
  login(callback) {
    const that = this
    wx.login({
      success(res) {
        if (res.code) {
          wx.request({
            url: that.globalData.apiBase + '/api/user/login',
            method: 'POST',
            header: { 'Content-Type': 'application/json' },
            data: {
              code: res.code,
              nickname: '微信用户',
              avatar_url: ''
            },
            success(resp) {
              if (resp.statusCode === 200) {
                const data = resp.data
                that.globalData.token = data.token
                that.globalData.userInfo = data.user
                wx.setStorageSync('token', data.token)
                wx.setStorageSync('userInfo', data.user)
                callback && callback(data)
              }
            }
          })
        }
      }
    })
  },

  /**
   * 获取 token，如果未登录则自动登录
   */
  getToken(callback) {
    if (this.globalData.token) {
      callback && callback(this.globalData.token)
    } else {
      this.login(function (data) {
        callback && callback(data.token)
      })
    }
  }
})
