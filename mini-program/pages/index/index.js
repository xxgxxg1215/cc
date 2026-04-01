const api = require('../../utils/api')

Page({
  data: {
    imagePath: '',
    weather: null,
    newsList: []
  },

  onLoad() {
    // 自动登录
    const app = getApp()
    app.getToken()
    this.loadWeather()
    this.loadNews()
  },

  onShow() {
    this.loadWeather()
  },

  // 加载天气
  loadWeather() {
    const that = this
    wx.getLocation({
      type: 'wgs84',
      success(res) {
        api.getWeather(res.latitude, res.longitude).then(data => {
          that.setData({ weather: data })
        }).catch(() => { })
      },
      fail() {
        // 无定位权限，使用默认
        api.getWeather(39.9, 116.4).then(data => {
          that.setData({ weather: data })
        }).catch(() => { })
      }
    })
  },

  // 加载最新资讯（首页只展示 3 条）
  loadNews() {
    api.getNewsList(1).then(data => {
      this.setData({ newsList: (data.list || []).slice(0, 3) })
    }).catch(() => { })
  },

  // 拍照识别
  onTakePhoto() {
    this.chooseImage('camera')
  },

  // 相册选择
  onChooseAlbum() {
    this.chooseImage('album')
  },

  chooseImage(sourceType) {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: [sourceType],
      sizeType: ['compressed'],
      success: (res) => {
        const filePath = res.tempFiles[0].tempFilePath
        this.setData({ imagePath: filePath })
        this.doPredict(filePath)
      }
    })
  },

  doPredict(filePath) {
    api.predict(filePath).then(result => {
      wx.navigateTo({
        url: '/pages/result/result',
        success(page) {
          page.eventChannel.emit('resultData', {
            imagePath: filePath,
            result: result
          })
        }
      })
    }).catch(err => {
      wx.showToast({
        title: err.message || '识别失败',
        icon: 'none',
        duration: 2500
      })
    })
  },

  // 跳转到新闻详情
  onTapNews(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/news-detail/news-detail?id=' + id })
  }
})
