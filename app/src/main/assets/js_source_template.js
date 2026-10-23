/**
 * JavaScript 单文件书源模板（新建入口默认内容）。
 *
 * 契约速查：
 * - 必备函数：search / getChapters / getContent（bookSourceType=file 时为 search / getBookInfo）；
 * - config.exploreUrl 非空 ⇒ 必须有 explore；
 * - 动态登录界面 loginUi(state) 与 loginAction(action, state, form) 成对声明，
 *   与 config.loginUi 数据**二选一**；
 * - 可用对象：java、source、sourceApi、cookie、cache、baseUrl 与内置 CryptoJS。
 * 保存时会校验以上契约，并自动重写 config.lastUpdateTime。
 */

var config = {
    bookSourceUrl: "https://example.com",
    bookSourceName: "示例 JS 书源",
    bookSourceType: 0,
    bookSourceGroup: "",
    bookSourceComment: "",
    // 表单登录示例: [{ name: "账号", type: "text" }, { name: "密码", type: "password" }]
    loginUi: [],
    // 发现分类支持 JSON 数组，或 "名称::url" 文本（换行 / && 分隔）
    exploreUrl: [],
    lastUpdateTime: 0
};

// config.loginUi 非空时必须提供。
function login() {
    var loginInfo = JSON.parse(source.getLoginInfo() || "{}");
    // 执行登录请求；失败时 throw "错误信息"。
}

/**
 * 动态登录界面（可选）：由 loginUi(state) 与 loginAction(action, state, form) 成对启用，
 * 不要同时填写 config.loginUi。支持 text、password、label、select、toggle、button 行。
 */

function search(key, page) {
    var html = java.ajax(
        config.bookSourceUrl + "/search?q=" + encodeURIComponent(key) + "&p=" + page
    );
    var books = [];
    // books.push({ name: "书名", bookUrl: "https://example.com/book/1", author: "作者" });
    return books;
}

// config.exploreUrl 非空时必须提供。url 原样传入，翻页请使用 page。
function explore(url, page) {
    var html = java.ajax(url);
    return [];
}

// 可选。返回字段会合并到搜索结果，tocUrl 为空时默认使用 bookUrl。
function getBookInfo(book) {
    var html = java.ajax(book.bookUrl);
    return {
        intro: "",
        coverUrl: "",
        latestChapterTitle: "",
        tocUrl: book.bookUrl
    };
}

// title 与 url 为必填字段，数组顺序即目录顺序。
function getChapters(book) {
    var html = java.ajax(book.tocUrl);
    var chapters = [];
    // chapters.push({ title: "第 1 章", url: "https://example.com/read/1" });
    return chapters;
}

// 返回正文文本，空字符串视为失败。
function getContent(chapter, book, nextChapterUrl) {
    var html = java.ajax(chapter.url);
    return html;
}
