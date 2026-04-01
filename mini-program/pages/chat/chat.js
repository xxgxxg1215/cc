const api = require('../../utils/api')

Page({
  data: {
    messages: [],
    inputValue: '',
    loading: false,
    scrollViewId: 'scroll-view',
    scrollIntoView: '',
    keyboardHeight: 0
  },

  onLoad() {
    this.setData({
      messages: [
        {
          id: 'welcome',
          role: 'assistant',
          content: '你好！我是农业顾问助手。我可以帮您回答农业相关的问题，比如：\n• 如何防治某种病害？\n• 这个季节种什么农作物？\n• 如何提高产量？\n\n请告诉我您的问题吧！'
        }
      ]
    })
  },

  onKeyboardHeightChange(e) {
    this.setData({ keyboardHeight: e.detail.height })
    this.scrollToBottom()
  },

  onInputChange(e) {
    this.setData({ inputValue: e.detail.value })
  },

  onSendMessage() {
    const message = this.data.inputValue.trim()
    if (!message) {
      wx.showToast({ title: '请输入问题', icon: 'none' })
      return
    }

    // 清空输入框
    this.setData({ inputValue: '' })

    // 添加用户消息
    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message
    }
    const messages = this.data.messages.concat([userMessage])
    this.setData({ messages: messages })
    this.scrollToBottom()

    // 发送到 AI
    this.setData({ loading: true })
    api.chatMessage(message)
      .then(response => {
        const assistantMessage = {
          id: Date.now().toString(),
          role: 'assistant',
          content: response.answer,
          isAgriculture: response.is_agriculture
        }
        this.setData({
          messages: messages.concat([assistantMessage]),
          loading: false
        })
        this.scrollToBottom()
      })
      .catch(error => {
        this.setData({ loading: false })
        wx.showToast({
          title: error.message || 'AI 服务出错',
          icon: 'none'
        })
      })
  },

  scrollToBottom() {
    setTimeout(() => {
      const scrollViewId = 'msg-' + this.data.messages[this.data.messages.length - 1].id
      this.setData({ scrollIntoView: scrollViewId })
    }, 100)
  }
})
