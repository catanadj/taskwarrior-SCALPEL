# scalpel/render/css/part02_base.py
from __future__ import annotations

CSS_PART = r'''  body {
    margin: 0;
    min-height: 100vh;
    background:
      radial-gradient(1200px 700px at 12% -8%, rgba(var(--accent-rgb), 0.12), transparent 62%),
      radial-gradient(900px 520px at 92% -10%, rgba(var(--warn-rgb), 0.08), transparent 58%),
      linear-gradient(165deg, #080f17 0%, var(--bg) 50%, #060b11 100%);
    color: var(--text);
    font: 14px/1.45 "IBM Plex Sans", "Avenir Next", "Segoe UI Variable", "Segoe UI", sans-serif;
    letter-spacing: 0.01em;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
    position: relative;
    isolation: isolate;
  }

  body.theme-light{
    background:
      radial-gradient(1000px 620px at 12% -10%, rgba(var(--accent-rgb), 0.11), transparent 62%),
      radial-gradient(920px 560px at 90% -12%, rgba(var(--warn-rgb), 0.08), transparent 58%),
      linear-gradient(165deg, #f8fafd 0%, var(--bg) 55%, #ecf3fa 100%);
  }
  body.theme-paper{
    background:
      radial-gradient(920px 560px at 14% -12%, rgba(var(--accent-rgb), 0.11), transparent 62%),
      radial-gradient(860px 520px at 96% -10%, rgba(var(--warn-rgb), 0.09), transparent 62%),
      linear-gradient(162deg, #fff9ef 0%, var(--bg) 54%, #f1e6d4 100%);
  }

  body::before,
  body::after{
    content: "";
    position: fixed;
    inset: -20vmax;
    pointer-events: none;
    z-index: -2;
  }
  body::before{
    background:
      radial-gradient(40% 40% at 15% 40%, rgba(var(--accent-rgb), 0.08), transparent 72%),
      radial-gradient(33% 33% at 88% 25%, rgba(var(--warn-rgb), 0.06), transparent 75%);
    filter: blur(18px) saturate(104%);
  }
  body::after{
    inset: 0;
    z-index: -1;
    opacity: 0.22;
    background-image:
      linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
    background-size: 42px 42px;
    mask-image: linear-gradient(180deg, rgba(0,0,0,0.55), rgba(0,0,0,0.08));
  }
  body.theme-light::after{
    opacity: 0.15;
    background-image:
      linear-gradient(rgba(16,33,54,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(16,33,54,0.04) 1px, transparent 1px);
  }
  body.theme-paper::after{
    opacity: 0.16;
    background-image:
      linear-gradient(rgba(111,93,73,0.07) 1px, transparent 1px),
      linear-gradient(90deg, rgba(111,93,73,0.04) 1px, transparent 1px);
    background-size: 36px 36px;
  }

  header, .layout, .modal-backdrop { position: relative; z-index: 1; }

  header { animation: page_reveal 560ms cubic-bezier(0.2, 0.7, 0.2, 1) both; }
  .layout > .card {
    opacity: 0;
    transform: translateY(10px);
    animation: panel_reveal 560ms cubic-bezier(0.2, 0.7, 0.2, 1) forwards;
  }
  .layout > .card:nth-child(1){ animation-delay: 80ms; }
  .layout > .card:nth-child(2){ animation-delay: 150ms; }
  .layout > .card:nth-child(3){ animation-delay: 220ms; }

  .title,
  .subtitle,
  .card .card-h,
  button,
  .seg,
  .pill{
    font-family: "Space Grotesk", "Avenir Next", "Segoe UI", sans-serif;
    letter-spacing: 0.015em;
  }

  input, select, textarea{
    font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
  }
  pre, code, .mono{
    font-family: "IBM Plex Mono", "SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace;
  }

  button,
  input,
  select,
  textarea{
    transition:
      border-color 130ms ease,
      box-shadow 130ms ease,
      background 130ms ease,
      color 130ms ease,
      transform 130ms ease;
  }

  :focus-visible{
    outline: 2px solid rgba(var(--accent-rgb), 0.64);
    outline-offset: 2px;
  }

  /* Shared spacing scale */
  .space-8,
  .space-10,
  .space-12,
  .space-14{
    width: 100%;
    flex: 0 0 auto;
    pointer-events: none;
  }
  .space-8{ height: 8px; }
  .space-10{ height: 10px; }
  .space-12{ height: 12px; }
  .space-14{ height: 14px; }

  @keyframes page_reveal{
    from{ opacity: 0; transform: translateY(-8px); }
    to{ opacity: 1; transform: translateY(0); }
  }
  @keyframes panel_reveal{
    from{ opacity: 0; transform: translateY(10px) scale(0.995); }
    to{ opacity: 1; transform: translateY(0) scale(1); }
  }

  @media (prefers-reduced-motion: reduce){
    header,
    .layout > .card{
      animation: none !important;
      opacity: 1 !important;
      transform: none !important;
    }
    button,
    input,
    select,
    textarea{
      transition: none !important;
    }
    .item{
      transition: none !important;
      transform: none !important;
    }
    .rsec-b{
      transition: none !important;
    }
    .lsec-b{
      transition: none !important;
    }
  }

  /* Compact density mode ("pro mode") */
  body.compact{
    --day-header-h: 64px;
  }
  body.compact header{
    padding: 8px 10px;
    gap: 7px;
  }
  body.compact header .subtitle{
    display: none;
  }
  body.compact header .title{
    font-size: 16px;
  }
  body.compact header .meta{
    font-size: 11px;
    padding: 2px 7px;
  }

  body.compact button{
    padding: 6px 8px;
    border-radius: 10px;
    font-size: 12px;
  }
  body.compact button.small{
    padding: 4px 7px;
    font-size: 11px;
  }
  body.compact .zoom,
  body.compact .viewwin{
    padding: 5px 8px;
    border-radius: 10px;
    gap: 5px;
  }
  body.compact .zoom .zlabel,
  body.compact .viewwin .vwlabel{
    font-size: 10px;
  }
  body.compact .zoom .zval{
    font-size: 11px;
    width: 64px;
  }
  body.compact .zoom input[type="range"]{
    width: 132px;
  }
  body.compact .viewwin input[type="date"],
  body.compact .viewwin select,
  body.compact .viewwin button.icon{
    height: 24px;
    font-size: 11px;
  }
  body.compact .viewwin button.icon{
    width: 25px;
    line-height: 22px;
  }

  body.compact .layout{
    gap: 10px;
    padding: 10px;
    height: calc(100vh - 66px);
    grid-template-columns: minmax(235px, 300px) minmax(0, 1fr) minmax(290px, 410px);
  }
  body.compact .card{
    border-radius: 12px;
  }
  body.compact .card .card-h{
    padding: 8px 10px;
    font-size: 11px;
  }
  body.compact .card .card-b{
    padding: 8px 10px;
  }
  body.compact .search{
    padding: 7px 9px;
    font-size: 12px;
  }

  body.compact .cal-wrap{
    grid-template-columns: 56px 1fr;
  }
  body.compact .time-tick .lbl{
    font-size: 11px;
    left: 6px;
  }
  body.compact .day-h{
    padding: 6px 8px;
    gap: 6px;
  }
  body.compact .day-h .dtop{
    font-size: 12px;
  }
  body.compact .day-h .dtop span{
    font-size: 11px;
  }
  body.compact .loadbar{
    height: 6px;
  }
  body.compact .loadtxt{
    font-size: 11px;
  }

  body.compact .evt{
    left: 5px;
    right: 5px;
  }
  body.compact .evt .evt-top{
    padding: 5px 7px;
  }
  body.compact .evt .evt-title{
    font-size: 12px;
  }
  body.compact .evt .evt-time{
    font-size: 11px;
  }
  body.compact .evt .evt-time .time-pill{
    padding: 1px 6px;
    font-size: 11px;
  }
  body.compact .evt .evt-bot{
    padding: 5px 7px 7px 7px;
    font-size: 11px;
  }

  body.compact .item{
    padding: 7px 8px;
    border-radius: 10px;
  }
  body.compact .item .line1{
    font-size: 12px;
  }
  body.compact .item .line2{
    font-size: 11px;
  }
  body.compact .pill{
    font-size: 10px;
    padding: 1px 7px;
  }

  body.compact .ops{
    gap: 6px;
    margin-bottom: 8px;
  }
  body.compact .rsec-h{
    padding: 7px 8px;
    gap: 8px;
  }
  body.compact .rsec-h .rsec-t{
    font-size: 12px;
  }
  body.compact .rsec-h .rsec-s{
    font-size: 10px;
  }
  body.compact .rsec-b{
    padding: 8px;
  }
  body.compact .lsec-h{
    padding: 7px 8px;
    gap: 8px;
  }
  body.compact .lsec-h .lsec-t{
    font-size: 11px;
  }
  body.compact .lsec-b{
    padding: 8px;
  }
  body.compact .hint{
    font-size: 11px;
  }
  body.compact .npill{
    font-size: 10px;
  }
  body.compact .note{
    font-size: 11px;
    padding: 5px 7px 12px 7px;
  }
  body.compact .note .nhdr{
    font-size: 10px;
  }

  @media (max-width: 820px){
    body.compact .layout{
      height: auto;
      grid-template-columns: 1fr;
    }
    body.compact header{
      padding: 7px 8px;
    }
    body.compact .zoom,
    body.compact .viewwin,
    body.compact .meta-row,
    body.compact header .btn{
      width: 100%;
    }
  }
'''
