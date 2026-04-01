const api = require('../../utils/api')
Page({
    data: { crops: [], currentCrop: '', list: [], keyword: '' },
    onLoad() {
        api.getCrops().then(data => {
            const crops = data.crops || []
            this.setData({ crops })
        })
        this.loadList()
    },
    loadList() {
        api.getEncyclopediaList(this.data.currentCrop, this.data.keyword).then(data => {
            this.setData({ list: data.list || [] })
        })
    },
    onSelectCrop(e) {
        const crop = e.currentTarget.dataset.crop
        this.setData({ currentCrop: crop === this.data.currentCrop ? '' : crop })
        this.loadList()
    },
    onSearch(e) {
        this.setData({ keyword: e.detail.value })
        this.loadList()
    },
    onTapItem(e) {
        const id = e.currentTarget.dataset.id
        wx.navigateTo({ url: '/pages/encyclopedia-detail/encyclopedia-detail?id=' + id })
    }
})
