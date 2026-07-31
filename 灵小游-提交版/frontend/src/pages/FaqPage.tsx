import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getFaqs, matchFaq, type FaqItem, type FaqMatchResult } from '../api/faq';

const CATEGORIES = ['全部', '开放时间', '票价', '演出', '路线推荐', '景点介绍', '文化背景', '餐饮', '住宿', '交通', '实用贴士'];

export function FaqPage() {
  const navigate = useNavigate();
  const [faqs, setFaqs] = useState<FaqItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [category, setCategory] = useState('全部');
  const [search, setSearch] = useState('');
  const [searchResult, setSearchResult] = useState<FaqMatchResult | null>(null);
  const [searching, setSearching] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const loadFaqs = useCallback(async (cat: string) => {
    setLoading(true);
    setError('');
    try {
      const data = cat === '全部' ? await getFaqs() : await getFaqs(cat);
      setFaqs(data);
    } catch {
      setError('FAQ 加载失败');
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadFaqs(category); }, [category, loadFaqs]);

  const handleSearch = useCallback(async () => {
    const q = search.trim();
    if (!q) { setSearchResult(null); return; }
    setSearching(true);
    try {
      const result = await matchFaq(q);
      setSearchResult(result);
      if (result.matched && result.faq) {
        setExpandedId(result.faq.id);
      }
    } catch { setSearchResult({ matched: false, score: 0, faq: null }); }
    setSearching(false);
  }, [search]);

  const filteredFaqs = searchResult?.matched && searchResult.faq
    ? faqs.filter((f) => f.id === searchResult.faq!.id)
    : faqs;

  return (
    <div className="faq-page">
      <header className="faq-header">
        <button className="favorites-back" onClick={() => navigate(-1)}>← 返回</button>
        <h1>常见问题</h1>
      </header>

      {/* Search bar */}
      <div className="faq-search-bar">
        <input
          className="faq-search-input"
          type="text"
          placeholder="输入问题搜索..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
        />
        <button className="faq-search-btn" onClick={handleSearch} disabled={searching}>
          {searching ? '搜索中...' : '搜索'}
        </button>
      </div>

      {searchResult && !searchResult.matched && (
        <div className="faq-no-match">未找到匹配的答案，试试换个关键词</div>
      )}

      {/* Category filter */}
      <div className="faq-categories">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            className={`faq-cat-tag${category === cat ? ' active' : ''}`}
            onClick={() => { setCategory(cat); setSearchResult(null); setSearch(''); }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* FAQ list */}
      {loading ? (
        <div className="faq-loading">加载中...</div>
      ) : error ? (
        <div className="faq-error">{error}</div>
      ) : filteredFaqs.length === 0 ? (
        <div className="faq-empty">该分类暂无常见问题</div>
      ) : (
        <div className="faq-list">
          {filteredFaqs.map((faq) => (
            <div key={faq.id} className={`faq-item${expandedId === faq.id ? ' expanded' : ''}`}>
              <button
                className="faq-question"
                onClick={() => setExpandedId(expandedId === faq.id ? null : faq.id)}
              >
                <span>{faq.question}</span>
                <span className="faq-arrow">{expandedId === faq.id ? '▾' : '▸'}</span>
              </button>
              {expandedId === faq.id && (
                <div className="faq-answer">
                  {faq.answer.split('\n').map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
