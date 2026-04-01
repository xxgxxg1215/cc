Page({
  data: {
    imagePath: '',
    result: null
  },

  onLoad() {
    const eventChannel = this.getOpenerEventChannel()
    eventChannel.on('resultData', (data) => {
      this.setData({
        imagePath: data.imagePath,
        result: data.result
      })
    })
  },

  // 重新识别
  onRetry() {
    wx.navigateBack()
  },

  // 预览图片
  onPreviewImage() {
    if (this.data.imagePath) {
      wx.previewImage({
        urls: [this.data.imagePath]
      })
    }
  }
})
