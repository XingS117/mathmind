const STYLE = `
@font-face {
  font-family: 'WenXing-SC';
  font-weight: 900;
  font-style: normal;
  font-display: block;
  src: url(data:font/woff2;base64,d09GMgABAAAAAATUABUAAAAACrQAAARqAAIKPQAAAAAAAAAAAAAAAAAAAAAAAAAAGYIKGyAcQj9IVkFSKgZgP1NUQVSBNicqADQvahEICoEQgRIwdgE2AiQDBgsGAAQgBYduByAXJBgGGzsJCJ4DbssMYSJKj1ZXpSs0pVI8QwTVGtmze48BJhUFwBapYgFYpaKiAVG4sAN0JHMGn5c/2WwBv7ZpHVbiIlsnlW4fhwt0BHkiwBhwOUy+6HYi9v4btlz6ckZhCaOQSEVwCFVq87fYXoYWjzAYjUOdoli+CNOaMMgX5nVTqwO/QUVKCUUkSM89176lEOpaCX5YSKty9NjSWoQumhruR+KyYbkPict1Sg9CV+kUHUJX60YVJDIHSaE9RqQ1zEFWqKsxTwvRZcbReZBZVIlWc9oVi0z6waP/Tdj1sDqg1BpHipf8+lpihKMNZA7bIOerzBHbIBDWoVBXoDlKMFwmJASf24BCrbb8UWxqlgooSwBse6hMdlmQBVmQBRZSWNKtNAUA6KSGp5NAzh8tZkY6kBrBpHg45pIiD1KdxIRqaBiR7Apgyd07zoMlKPYFAQGpQ7qHjsyFUC3QlAXaBta2e5SyQn2dxSvWbth8GohkMVgMXrI7lKMveEXMGaKIufBqj4KkFxVxDMK/caUy/iDpdOApVKV763TuKIXqvEts8c0JEKofeQQash7SFK4bPeH5jyD4tQDxVyYygYSMpmiBprQ6gkIhWPJyM1i+ARSIhjTiNr7au7ja2ykqoiZq15qoE3Xb+0LUi/posUE07CsahTM0VZqEK/RTolm4y1NBtECJctTiSSp8dXcwGHbOuK9evaJ6bberNx/WLp72uN94ckd/7dajuoXjvbtef3y7vt4JjovCNl9rxSy//nfqdvbOF5VON3emO/dOSzuTHXY9idPn01acrev+cDMXNDXJbBE9Tpxzzli7xH3Wb3bq/L4FYsP500fERgACAVrTyNMG+m+jUGv6ZEK3swwrRocFWr3/9Ojq4eYywT/A+eudKyevv3v/ydHx01NjW2Xx8ZN35oR8u3n18u1nX31zqzN88S6x0xtLmN9vXt8+e55lDx36H8yEhf6XJ7MTAql2yJ/LqdMdDql/LXP+Bh8uMWsBvsym9+HL8sGcBSolEORvZSLkbwZgoW0U+SORv1mMRyHpTgswEbX2oaBFUYMTsEJoaSmS+i4hG+4IFygqTPRfV6l9FKZDhkWRVMdSZLWxBoXGMckVZ6hUNw6gSnUcR7XaOIkadeMU19ZwHRauW4l6OsYurl+PBnrGVW6oaISJv9yYC00EJcJNGdGMf8rm5rzHtEBSp/UIiUAUi108hkREZDFS6cmIcN1GjRqUjMebcGWODv0NHAPVAF6EaMSEHqO6EdVkI2TDxsmMiHwqxSiinM4AGRGmhmrMMANZGE451SgVUUNHMaL+nNxru4zppzNMwhEIYqXIkitbhZQMl9msm1WrWw/lwGIiW556wu4RPVQKkmszIYklOkuUJNul/pMYghQKlYI1TNZPpjNCrnbp7aV6dOk2KpdsQM9GKpOMl48ZkE3VzyhbPx2DPg3kg0kqNyjFWPHk+PClJ0AZ8ySgq8l4Jf3itMlkuZOkOhqi/vyv+72YG5d3grAG3wAA) format('woff2');
}
`;

const ANIMATIONS = `
#wx-star-path { stroke-dasharray: 1; stroke-dashoffset: 1; animation: wx-star-draw 1200ms cubic-bezier(0.65,0,0.35,1) 200ms forwards; }
@keyframes wx-star-draw { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }
#wx-wen-character { opacity: 0; transform-box: fill-box; transform-origin: center; transform: scale(0.9); animation: wx-wen-reveal 400ms cubic-bezier(0.16,1,0.3,1) 1100ms forwards, wx-wen-pulse 2000ms ease-in-out 1500ms infinite alternate; }
@keyframes wx-wen-reveal { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }
@keyframes wx-wen-pulse { from { opacity: 0.85; } to { opacity: 1; } }
#wx-logo-root { transform-box: fill-box; transform-origin: center; animation: wx-breathe 4000ms ease-in-out 1500ms infinite alternate; }
@keyframes wx-breathe { from { transform: scale(1); } to { transform: scale(1.02); } }
@media (prefers-reduced-motion: reduce) { #wx-star-path { stroke-dashoffset: 0; animation: none; } #wx-wen-character { opacity: 1; transform: scale(1); animation: none; } #wx-logo-root { animation: none; } }
`;

export default function WenXingLogo() {
  return (
    <>
      <style>{STYLE}{ANIMATIONS}</style>
      <div style={{ width: 52, height: 52, flexShrink: 0, borderRadius: 10, overflow: "hidden" }}>
        <svg id="wx-logo-root" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400"
          role="img" aria-label="文星" style={{ width: "100%", height: "100%", display: "block" }}>
          <defs>
            <linearGradient id="wx-bg" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#1e40af"/>
              <stop offset="100%" stopColor="#4f46e5"/>
            </linearGradient>
          </defs>
          <rect x="8" y="8" width="384" height="384" rx="44" fill="url(#wx-bg)"/>
          <title>文星</title>
          <g fill="none" stroke="#ffffff" strokeWidth="18" strokeLinejoin="round" strokeLinecap="round">
            <path id="wx-star-path" pathLength="1" d="M 200 30 L 246 158 L 384 158 L 274 240 L 320 370 L 200 290 L 80 370 L 126 240 L 16 158 L 154 158 Z"/>
          </g>
          <g id="wx-wen-character"
            fontFamily="-apple-system,'WenXing-SC','Noto Sans SC',sans-serif"
            fontWeight="900" textAnchor="middle">
            <text x="200" y="228" fontSize="150" dy="0.35em"
              fill="#fde047" stroke="#1E3A8A" strokeWidth="6"
              paintOrder="stroke fill">文</text>
          </g>
        </svg>
      </div>
    </>
  );
}
