const api = require('../../utils/api')
Page({
    data: { title: '', content: '' },
    onTitleInput(e) { this.setData({ title: e.detail.value }) },
    onContentInput(e) { this.setData({ content: e.detail.value }) },
    onSubmit() {
        if (!this.data.title.trim()) return wx.showToast({ title: '请输入标题', icon: 'none' })
        if (!this.data.content.trim()) return wx.showToast({ title: '请输入内容', icon: 'none' })
        wx.showLoading({ title: '发布中...' })
        api.createPost({ title: this.data.title, content: this.data.content }).then(() => {
            wx.hideLoading()
            wx.showToast({ title: '发布成功', icon: 'success' })
            setTimeout(() => wx.navigateBack(), 1200)
        }).catch(() => {
            wx.hideLoading()
            wx.showToast({ title: '发布失败', icon: 'none' })
        })
    }
})
