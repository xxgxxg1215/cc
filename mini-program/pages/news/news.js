const api = require('../../utils/api')
Page({
    data: { newsList: [], page: 1, noMore: false, loading: false },
    onLoad() { this.loadNews() },
    loadNews() {
        if (this.data.loading || this.data.noMore) return
        this.setData({ loading: true })
        api.getNewsList(this.data.page).then(data => {
            const list = this.data.newsList.concat(data.list || [])
            this.setData({ newsList: list, loading: false, noMore: list.length >= data.total, page: this.data.page + 1 })
        }).catch(() => this.setData({ loading: false }))
    },
    onReachBottom() { this.loadNews() },
    onTapNews(e) { wx.navigateTo({ url: '/pages/news-detail/news-detail?id=' + e.currentTarget.dataset.id }) }
})
