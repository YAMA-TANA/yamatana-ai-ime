(() => {
  'use strict';

  if (!window.pdfjsLib || !window.PDFLib) {
    const status=document.getElementById('status');
    if(status){
      status.textContent='PDF engine failed to load. Check your connection and reload.';
      status.classList.add('show');
    }
    document.querySelectorAll('button,input,select,textarea').forEach(el=>{ if(el.id!=='languageSelect') el.disabled=true; });
    return;
  }

  const packs = window.PDFWB_I18N;
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  let lang = localStorage.getItem('pdf-workbench-language') || 'ja';
  const t = k => (packs[lang] && packs[lang][k]) || packs.en[k] || k;

  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

  let pdf = null;
  let pdfBytes = null;
  let sourceName = 'document.pdf';
  let pages = [];
  let currentId = null;
  let scale = 1.15;
  let tool = 'select';
  let drawing = null;
  let mainRenderTask = null;
  let renderToken = 0;
  let thumbObserver = null;
  let history = [];
  let future = [];
  let busy = false;
  let idCounter = 0;

  function makeId(){ return `p${Date.now().toString(36)}-${(++idCounter).toString(36)}`; }
  function currentPage(){ return pages.find(p => p.id === currentId) || null; }
  function currentIndex(){ return pages.findIndex(p => p.id === currentId); }

  function applyLanguage(){
    document.documentElement.lang = lang;
    document.title = t('title');
    $$('[data-i18n]').forEach(e => { if (t(e.dataset.i18n) != null) e.textContent = t(e.dataset.i18n); });
    $$('[data-i18n-placeholder]').forEach(e => e.placeholder = t(e.dataset.i18nPlaceholder));
    $('#languageSelect').value = lang;
    if (!pdf) $('#fileMeta').textContent = t('noFile');
    renderPageList();
    updateControls();
  }

  function toast(message, ms=2200){
    const e = $('#status');
    e.textContent = message;
    e.classList.add('show');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => e.classList.remove('show'), ms);
  }

  function setBusy(on, message=''){
    busy = on;
    $('#busy').classList.toggle('show', on);
    if (message) $('#busyText').textContent = message;
    updateControls();
  }

  function snapshot(){
    return {pages:structuredClone(pages),currentId};
  }

  function restore(state){
    pages = structuredClone(state.pages);
    currentId = state.currentId && pages.some(p => p.id === state.currentId) ? state.currentId : pages[0]?.id || null;
    renderAll();
  }

  function pushHistory(){
    if (!pdf) return;
    history.push(snapshot());
    if (history.length > 60) history.shift();
    future = [];
    updateControls();
  }

  function undo(){
    if (!history.length || busy) return;
    future.push(snapshot());
    restore(history.pop());
    toast(t('undo'));
  }

  function redo(){
    if (!future.length || busy) return;
    history.push(snapshot());
    restore(future.pop());
    toast(t('redo'));
  }

  function updateControls(){
    const has = !!pdf && pages.length > 0;
    const idx = currentIndex();
    $('#exportTop').disabled = !has || busy;
    $('#prevPage').disabled = !has || idx <= 0 || busy;
    $('#nextPage').disabled = !has || idx < 0 || idx >= pages.length - 1 || busy;
    $('#pageNumber').disabled = !has || busy;
    $('#zoomIn').disabled = !has || busy;
    $('#zoomOut').disabled = !has || busy;
    $('#fitPage').disabled = !has || busy;
    $('#moveUp').disabled = !has || idx <= 0 || busy;
    $('#moveDown').disabled = !has || idx < 0 || idx >= pages.length - 1 || busy;
    $('#duplicatePage').disabled = !has || busy;
    $('#rotatePage').disabled = !has || busy;
    $('#deletePage').disabled = !has || pages.length <= 1 || busy;
    $('#clearAnnotations').disabled = !has || !(currentPage()?.annotations?.length) || busy;
    $('#undoTop').disabled = !history.length || busy;
    $('#redoTop').disabled = !future.length || busy;
    $('#pageTotal').textContent = has ? `/ ${pages.length}` : '/ —';
    $('#pageNumber').value = has ? idx + 1 : 1;
    $('#zoomValue').textContent = `${Math.round(scale * 100)}%`;
    $('#topStatus').textContent = has ? `${sourceName} · ${pages.length} ${t('pages').toLowerCase?.() || 'pages'}` : 'Private, local-first PDF editing';
  }

  async function openFile(file){
    if (!file) return;
    const looksPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
    if (!looksPdf){ toast(t('invalid')); return; }
    if (file.size > 200 * 1024 * 1024){ toast(t('tooLarge'), 3200); return; }

    setBusy(true, t('loading'));
    try{
      if (mainRenderTask) { try { mainRenderTask.cancel(); } catch {} }
      if (pdf?.destroy) { try { await pdf.destroy(); } catch {} }
      pdf = null;
      pdfBytes = await file.arrayBuffer();
      const loadingTask = pdfjsLib.getDocument({
        data: new Uint8Array(pdfBytes),
        enableXfa: true,
        isEvalSupported: false
      });
      loadingTask.onPassword = (updatePassword, reason) => {
        const password = window.prompt(reason === pdfjsLib.PasswordResponses.INCORRECT_PASSWORD ? t('passwordWrong') : t('password'));
        if (password == null) loadingTask.destroy();
        else updatePassword(password);
      };
      pdf = await loadingTask.promise;
      if (pdf.numPages > 1500){
        await loadingTask.destroy();
        pdf = null;
        pdfBytes = null;
        toast(t('tooMany'), 3200);
        return;
      }
      sourceName = file.name || 'document.pdf';
      try {
        await PDFLib.PDFDocument.load(pdfBytes, {updateMetadata:false});
      } catch (preflightError) {
        if (/encrypt/i.test(String(preflightError?.name||'') + ' ' + String(preflightError?.message||''))) {
          throw new Error('ENCRYPTED_PDF_UNSUPPORTED');
        }
        throw preflightError;
      }
      pages = Array.from({length:pdf.numPages}, (_, i) => ({
        id: makeId(),
        sourceIndex: i,
        rotation: 0,
        annotations: []
      }));
      currentId = pages[0]?.id || null;
      history = [];
      future = [];
      scale = 1.15;
      $('#fileMeta').textContent = `${sourceName} · ${(file.size/1024/1024).toFixed(2)} MB · ${pdf.numPages} pages`;
      $('#emptyStage').style.display = 'none';
      $('#pageShell').classList.add('visible');
      await renderAll(false);
      requestAnimationFrame(() => fitPage(false));
      toast(t('ready'));
      report('open_pdf');
    }catch(err){
      console.error(err);
      pdf = null; pdfBytes = null; pages = []; currentId = null;
      $('#emptyStage').style.display = 'grid';
      $('#pageShell').classList.remove('visible');
      $('#fileMeta').textContent = t('noFile');
      renderPageList();
      toast(err?.message==='ENCRYPTED_PDF_UNSUPPORTED' ? (t('encryptedUnsupported')||t('invalid')) : t('invalid'), 3200);
    }finally{
      setBusy(false);
      $('#fileInput').value = '';
    }
  }

  async function renderAll(forceThumbs=false){
    updateControls();
    renderPageList(forceThumbs);
    updateAnnotationList();
    await renderMainPage();
  }

  function effectiveRotation(model, pdfPage){
    return (((pdfPage?.rotate || 0) + (model?.rotation || 0)) % 360 + 360) % 360;
  }

  function selectPage(id){
    if (!pages.some(p=>p.id===id)) return;
    currentId=id;
    $$('.page-item').forEach(item=>item.classList.toggle('active',item.dataset.id===id));
    const active=$(`.page-item[data-id="${CSS.escape(id)}"]`);
    active?.scrollIntoView({block:'nearest'});
    updateControls();
    updateAnnotationList();
    renderMainPage();
  }

  function updateCurrentPageListMeta(){
    const model=currentPage();
    if(!model)return;
    const item=$(`.page-item[data-id="${CSS.escape(model.id)}"]`);
    if(!item)return;
    const label=item.querySelector('.page-label span');
    if(label) label.textContent=`✎ ${model.annotations.length}`;
  }

  async function renderMainPage(){
    const model = currentPage();
    if (!pdf || !model) return;
    const token = ++renderToken;
    if (mainRenderTask){ try { mainRenderTask.cancel(); } catch {} }

    try{
      const page = await pdf.getPage(model.sourceIndex + 1);
      if (token !== renderToken) return;
      const rotation=effectiveRotation(model,page);
      const viewport = page.getViewport({scale, rotation});
      const canvas = $('#pdfCanvas');
      const ctx = canvas.getContext('2d', {alpha:false});
      let dpr = Math.min(window.devicePixelRatio || 1, 2);
      const maxCanvasPixels = 16_000_000;
      const requestedPixels = viewport.width * viewport.height * dpr * dpr;
      if (requestedPixels > maxCanvasPixels) dpr *= Math.sqrt(maxCanvasPixels / requestedPixels);
      canvas.width = Math.max(1, Math.floor(viewport.width * dpr));
      canvas.height = Math.max(1, Math.floor(viewport.height * dpr));
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      $('#pageShell').style.width = `${viewport.width}px`;
      $('#pageShell').style.height = `${viewport.height}px`;
      $('#overlay').style.width = `${viewport.width}px`;
      $('#overlay').style.height = `${viewport.height}px`;

      const renderViewport = page.getViewport({scale:scale*dpr, rotation});
      mainRenderTask = page.render({canvasContext:ctx, viewport:renderViewport});
      await mainRenderTask.promise;
      if (token !== renderToken) return;
      renderOverlay();
      updateAnnotationList();
      updateControls();
    }catch(err){
      if (err?.name !== 'RenderingCancelledException') console.error(err);
    }finally{
      mainRenderTask = null;
    }
  }

  function renderPageList(force=false){
    const list = $('#pageList');
    if (!pdf || !pages.length){ list.innerHTML=''; return; }
    if (thumbObserver) thumbObserver.disconnect();
    list.innerHTML = '';

    thumbObserver = new IntersectionObserver(entries => {
      for (const entry of entries){
        if (!entry.isIntersecting) continue;
        const canvas = entry.target.querySelector('canvas');
        if (canvas && !canvas.dataset.rendered) renderThumbnail(entry.target, canvas);
        thumbObserver.unobserve(entry.target);
      }
    }, {root:list, rootMargin:'180px 0px'});

    pages.forEach((model, index) => {
      const item = document.createElement('div');
      item.className = `page-item${model.id===currentId?' active':''}`;
      item.dataset.id = model.id;
      item.draggable = true;
      item.innerHTML = `<div class="thumb-wrap"><canvas aria-hidden="true"></canvas></div><div class="page-label"><b>${t('page')} ${index+1}</b><span>✎ ${model.annotations.length}</span></div>`;
      item.onclick = () => {
        if (currentId === model.id) return;
        selectPage(model.id);
      };
      item.addEventListener('dragstart', () => item.classList.add('dragging'));
      item.addEventListener('dragend', () => { item.classList.remove('dragging'); $$('.page-item').forEach(x=>x.classList.remove('drag-over')); });
      item.addEventListener('dragover', e => { e.preventDefault(); item.classList.add('drag-over'); });
      item.addEventListener('dragleave', () => item.classList.remove('drag-over'));
      item.addEventListener('drop', e => {
        e.preventDefault();
        const fromEl = $('.page-item.dragging');
        if (!fromEl || fromEl === item) return;
        const from = pages.findIndex(p=>p.id===fromEl.dataset.id);
        const to = pages.findIndex(p=>p.id===item.dataset.id);
        if (from < 0 || to < 0) return;
        pushHistory();
        const [moved] = pages.splice(from,1);
        pages.splice(to,0,moved);
        renderPageList();
        updateControls();
        toast(t('moved'));
      });
      list.appendChild(item);
      if (force) {
        const canvas = item.querySelector('canvas');
        requestAnimationFrame(() => renderThumbnail(item, canvas));
      } else thumbObserver.observe(item);
    });

    const active = list.querySelector('.page-item.active');
    if (active && !active.matches(':hover')) active.scrollIntoView({block:'nearest'});
  }

  async function renderThumbnail(item, canvas){
    if (!pdf || !document.body.contains(item)) return;
    const model = pages.find(p=>p.id===item.dataset.id);
    if (!model) return;
    try{
      const page = await pdf.getPage(model.sourceIndex + 1);
      if (!document.body.contains(item)) return;
      const rotation=effectiveRotation(model,page);
      const base = page.getViewport({scale:1, rotation});
      const maxW = 210, maxH = 250;
      const s = Math.min(maxW/base.width, maxH/base.height, .42);
      const viewport = page.getViewport({scale:s, rotation});
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = Math.max(1,Math.floor(viewport.width*dpr));
      canvas.height = Math.max(1,Math.floor(viewport.height*dpr));
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      await page.render({canvasContext:canvas.getContext('2d',{alpha:false}),viewport:page.getViewport({scale:s*dpr,rotation})}).promise;
      canvas.dataset.rendered='1';
    }catch(err){ console.warn('thumbnail render failed', err); }
  }

  function displayPoint(e){
    const r = $('#overlay').getBoundingClientRect();
    return {
      x: Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),
      y: Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))
    };
  }

  function renderOverlay(){
    const o = $('#overlay');
    o.innerHTML = '';
    const model = currentPage();
    if (!model) return;
    for (const a of model.annotations){
      if (a.kind === 'pen'){
        let svg = o.querySelector('svg');
        if (!svg){ svg=document.createElementNS('http://www.w3.org/2000/svg','svg'); o.appendChild(svg); }
        const p=document.createElementNS('http://www.w3.org/2000/svg','polyline');
        p.setAttribute('points',a.points.map(q=>`${q.x*100}%,${q.y*100}%`).join(' '));
        p.style.stroke=a.color;
        p.style.strokeWidth=`${Math.max(1,a.lineWidth*scale)}px`;
        svg.appendChild(p);
        continue;
      }
      const d=document.createElement('div');
      d.className=`overlay-item overlay-${a.kind}`;
      d.style.left=`${a.x*100}%`; d.style.top=`${a.y*100}%`; d.style.width=`${a.w*100}%`; d.style.height=`${a.h*100}%`;
      if (a.kind==='text'){
        d.textContent=a.text;
        d.style.fontSize=`${Math.max(8,a.fontSize*scale)}px`;
        d.style.color=a.color;
      }else if(a.kind==='highlight'){
        d.style.background=a.color; d.style.opacity=String(a.opacity/100*.7);
      }else if(a.kind==='whiteout'){
        d.style.opacity=String(a.opacity/100);
      }
      o.appendChild(d);
    }
  }

  function addAnnotation(a){
    const model = currentPage();
    if (!model) return;
    pushHistory();
    model.annotations.push(a);
    renderOverlay();
    updateAnnotationList();
    updateCurrentPageListMeta();
    updateControls();
  }

  function updateAnnotationList(){
    const list=$('#annotationList');
    const items=currentPage()?.annotations || [];
    $('#annotationCount').textContent=String(items.length);
    list.innerHTML='';
    items.forEach((a,i)=>{
      const row=document.createElement('div');
      row.className='annotation-row';
      const label=document.createElement('span');
      label.textContent=a.kind==='text'?a.text:a.kind;
      const del=document.createElement('button');
      del.type='button'; del.textContent='×'; del.setAttribute('aria-label','Delete annotation');
      del.onclick=()=>{ pushHistory(); currentPage().annotations.splice(i,1); renderOverlay(); updateAnnotationList(); updateCurrentPageListMeta(); updateControls(); };
      row.append(label,del); list.appendChild(row);
    });
  }

  function setTool(next){
    tool=next;
    $$('.tool').forEach(b=>b.classList.toggle('active',b.dataset.tool===next));
    $('#overlay').style.cursor=next==='select'?'default':next==='text'?'text':'crosshair';
  }

  function onPointerDown(e){
    if (!pdf || busy || tool==='select') return;
    const p=displayPoint(e);
    if(tool==='text'){
      const text=$('#textValue').value.trim();
      if(!text){toast(t('textNeeded'));return}
      addAnnotation({kind:'text',x:p.x,y:p.y,w:.42,h:.08,text,fontSize:Number($('#fontSize').value),color:$('#inkColor').value});
      return;
    }
    drawing={start:p,points:[p],pointerId:e.pointerId};
    $('#overlay').setPointerCapture?.(e.pointerId);
  }

  function onPointerMove(e){
    if(!drawing || e.pointerId!==drawing.pointerId) return;
    const p=displayPoint(e);
    if (tool==='pen'){
      const last=drawing.points[drawing.points.length-1];
      if (!last || Math.hypot(p.x-last.x,p.y-last.y) > .002) drawing.points.push(p);
      renderOverlay();
      let svg=$('#overlay').querySelector('svg');
      if(!svg){svg=document.createElementNS('http://www.w3.org/2000/svg','svg');$('#overlay').appendChild(svg)}
      const line=document.createElementNS('http://www.w3.org/2000/svg','polyline');
      line.setAttribute('points',drawing.points.map(q=>`${q.x*100}%,${q.y*100}%`).join(' '));
      line.style.stroke=$('#inkColor').value;
      line.style.strokeWidth=`${Number($('#lineWidth').value)*scale}px`;
      svg.appendChild(line);
    } else drawing.points=[drawing.start,p];
  }

  function onPointerUp(e){
    if(!drawing || e.pointerId!==drawing.pointerId) return;
    const end=displayPoint(e), start=drawing.start;
    if(tool==='pen'){
      if(drawing.points.length>1) addAnnotation({kind:'pen',points:drawing.points,color:$('#inkColor').value,lineWidth:Number($('#lineWidth').value)});
    }else{
      const x=Math.min(start.x,end.x),y=Math.min(start.y,end.y);
      const w=Math.abs(start.x-end.x),h=Math.abs(start.y-end.y);
      if(w>.003 && h>.003) addAnnotation({kind:tool,x,y,w,h,opacity:Number($('#opacity').value),color:$('#inkColor').value});
    }
    try{$('#overlay').releasePointerCapture?.(e.pointerId)}catch{}
    drawing=null;
    renderOverlay();
  }

  function movePage(dir){
    const i=currentIndex(),j=i+dir;
    if(i<0||j<0||j>=pages.length)return;
    pushHistory();
    [pages[i],pages[j]]=[pages[j],pages[i]];
    renderPageList(); updateControls(); toast(t('moved'));
  }

  function deletePage(){
    const i=currentIndex();
    if(i<0)return;
    if(pages.length<=1){toast(t('lastPage'));return}
    pushHistory();
    pages.splice(i,1);
    currentId=pages[Math.min(i,pages.length-1)].id;
    renderAll();
    toast(t('removed'));
  }

  function duplicatePage(){
    const i=currentIndex(),model=currentPage();
    if(i<0||!model)return;
    pushHistory();
    const copy=structuredClone(model);
    copy.id=makeId();
    copy.annotations=structuredClone(model.annotations);
    pages.splice(i+1,0,copy);
    currentId=copy.id;
    renderAll();
    toast(t('duplicated'));
  }

  function rotatePage(){
    const model=currentPage();
    if(!model)return;
    pushHistory();
    model.rotation=(model.rotation+90)%360;
    renderAll();
    requestAnimationFrame(()=>fitPage(false));
    toast(t('rotated'));
  }

  function clearAnnotations(){
    const model=currentPage();
    if(!model?.annotations.length)return;
    pushHistory();
    model.annotations=[];
    renderOverlay(); updateAnnotationList(); updateCurrentPageListMeta(); updateControls();
    toast(t('cleared'));
  }

  function fitPage(render=true){
    const model=currentPage();
    if(!pdf||!model)return;
    pdf.getPage(model.sourceIndex+1).then(page=>{
      const base=page.getViewport({scale:1,rotation:effectiveRotation(model,page)});
      const stage=$('#stage').getBoundingClientRect();
      const availableW=Math.max(120,stage.width-48);
      const availableH=Math.max(120,stage.height-48);
      scale=Math.max(.2,Math.min(3,availableW/base.width,availableH/base.height));
      updateControls();
      if(render) renderMainPage();
      else renderMainPage();
    });
  }

  function hexToRgb(hex){
    const h=(hex||'#000000').replace('#','');
    const n=parseInt(h.length===3?h.split('').map(c=>c+c).join(''):h,16);
    return PDFLib.rgb(((n>>16)&255)/255,((n>>8)&255)/255,(n&255)/255);
  }

  async function annotationPdfGeometry(model, ann){
    const srcPage=await pdf.getPage(model.sourceIndex+1);
    const viewport=srcPage.getViewport({scale:1,rotation:effectiveRotation(model,srcPage)});
    const toPdf=(u,v)=>viewport.convertToPdfPoint(u*viewport.width,v*viewport.height);
    if(ann.kind==='pen') return {viewport,toPdf};
    const corners=[toPdf(ann.x,ann.y),toPdf(ann.x+ann.w,ann.y),toPdf(ann.x,ann.y+ann.h),toPdf(ann.x+ann.w,ann.y+ann.h)];
    const xs=corners.map(p=>p[0]), ys=corners.map(p=>p[1]);
    return {x:Math.min(...xs),y:Math.min(...ys),w:Math.max(...xs)-Math.min(...xs),h:Math.max(...ys)-Math.min(...ys),viewport,toPdf};
  }

  function wrapText(ctx,text,maxWidth){
    const lines=[];
    for(const paragraph of String(text).split(/\r?\n/)){
      if(!paragraph){lines.push('');continue}
      let line='';
      for(const char of [...paragraph]){
        const test=line+char;
        if(line && ctx.measureText(test).width>maxWidth){lines.push(line);line=char}else line=test;
      }
      if(line)lines.push(line);
    }
    return lines.length?lines:[''];
  }

  async function makeTextPng(text,color,fontSizePt,maxWidthPt,maxHeightPt){
    const ratio=2;
    const canvas=document.createElement('canvas');
    const ctx=canvas.getContext('2d');
    const fontPx=Math.max(8,fontSizePt*ratio);
    ctx.font=`600 ${fontPx}px Arial, "Noto Sans", sans-serif`;
    const maxWidthPx=Math.max(40,maxWidthPt*ratio);
    const lines=wrapText(ctx,text,maxWidthPx);
    const lineHeight=fontPx*1.25;
    const width=Math.max(10,Math.min(maxWidthPx,Math.max(...lines.map(x=>ctx.measureText(x).width),10)));
    const height=Math.max(lineHeight,Math.min(maxHeightPt*ratio||lineHeight*lines.length,lineHeight*lines.length));
    canvas.width=Math.ceil(width+4*ratio);
    canvas.height=Math.ceil(height+4*ratio);
    const c=canvas.getContext('2d');
    c.scale(ratio,ratio);
    c.font=`600 ${fontSizePt}px Arial, "Noto Sans", sans-serif`;
    c.textBaseline='top';
    c.fillStyle=color;
    lines.forEach((line,i)=>c.fillText(line,2,2+i*fontSizePt*1.25,Math.max(20,maxWidthPt)));
    return canvas.toDataURL('image/png');
  }

  async function exportPdf(){
    if(!pdfBytes||!pages.length||busy){if(!pdfBytes)toast(t('needPdf'));return}
    setBusy(true,t('exporting'));
    try{
      const src=await PDFLib.PDFDocument.load(pdfBytes,{ignoreEncryption:false});
      const out=await PDFLib.PDFDocument.create();

      for(const model of pages){
        const [page]=await out.copyPages(src,[model.sourceIndex]);
        out.addPage(page);
        const srcPdfPage=await pdf.getPage(model.sourceIndex+1);
        page.setRotation(PDFLib.degrees(effectiveRotation(model,srcPdfPage)));

        for(const a of model.annotations){
          if(a.kind==='pen'){
            const {toPdf}=await annotationPdfGeometry(model,a);
            for(let j=1;j<a.points.length;j++){
              const p1=toPdf(a.points[j-1].x,a.points[j-1].y);
              const p2=toPdf(a.points[j].x,a.points[j].y);
              page.drawLine({start:{x:p1[0],y:p1[1]},end:{x:p2[0],y:p2[1]},thickness:Math.max(.7,a.lineWidth),color:hexToRgb(a.color)});
            }
            continue;
          }

          const g=await annotationPdfGeometry(model,a);
          if(a.kind==='highlight'||a.kind==='whiteout'){
            page.drawRectangle({
              x:g.x,y:g.y,width:g.w,height:g.h,
              color:a.kind==='whiteout'?PDFLib.rgb(1,1,1):hexToRgb(a.color),
              opacity:a.kind==='whiteout'?1:a.opacity/100,
              borderWidth:0
            });
          }else if(a.kind==='text'){
            const pngUrl=await makeTextPng(a.text,a.color,a.fontSize,Math.max(20,g.w),Math.max(20,g.h));
            const img=await out.embedPng(pngUrl);
            const aspect=img.width/img.height;
            let dw=g.w,dh=dw/aspect;
            if(dh>g.h){dh=g.h;dw=dh*aspect}
            page.drawImage(img,{x:g.x,y:g.y+Math.max(0,g.h-dh),width:dw,height:dh});
          }
        }
      }

      out.setTitle(sourceName.replace(/\.pdf$/i,''));
      out.setProducer('PDF WORKBENCH');
      out.setCreator('PDF WORKBENCH');
      const bytes=await out.save({useObjectStreams:true});
      const blob=new Blob([bytes],{type:'application/pdf'});
      const url=URL.createObjectURL(blob);
      const a=document.createElement('a');
      a.href=url;
      a.download=`edited-${sourceName.replace(/\.pdf$/i,'')}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(()=>URL.revokeObjectURL(url),5000);
      toast(t('saved'));
      report('export_pdf');
    }catch(err){
      console.error(err);
      toast(t('invalid'),3200);
    }finally{
      setBusy(false);
    }
  }

  async function report(){}

  $('#languageSelect').onchange=e=>{lang=e.target.value;localStorage.setItem('pdf-workbench-language',lang);applyLanguage()};
  $('#fileInput').onchange=e=>openFile(e.target.files?.[0]);
  $('#dropzone').ondragover=e=>{e.preventDefault();$('#dropzone').classList.add('drag')};
  $('#dropzone').ondragleave=()=>$('#dropzone').classList.remove('drag');
  $('#dropzone').ondrop=e=>{e.preventDefault();$('#dropzone').classList.remove('drag');openFile(e.dataTransfer.files?.[0])};

  $('#overlay').addEventListener('pointerdown',onPointerDown);
  $('#overlay').addEventListener('pointermove',onPointerMove);
  $('#overlay').addEventListener('pointerup',onPointerUp);
  $('#overlay').addEventListener('pointercancel',e=>{drawing=null;try{$('#overlay').releasePointerCapture?.(e.pointerId)}catch{};renderOverlay()});

  $$('.tool').forEach(b=>b.onclick=()=>setTool(b.dataset.tool));
  $('#fontSize').oninput=e=>$('#fontSizeOutput').textContent=`${e.target.value} pt`;
  $('#lineWidth').oninput=e=>$('#lineWidthOutput').textContent=`${e.target.value} pt`;
  $('#opacity').oninput=e=>$('#opacityOutput').textContent=`${e.target.value}%`;

  $('#prevPage').onclick=()=>{const i=currentIndex();if(i>0){currentId=pages[i-1].id;renderAll()}};
  $('#nextPage').onclick=()=>{const i=currentIndex();if(i>=0&&i<pages.length-1){currentId=pages[i+1].id;renderAll()}};
  $('#pageNumber').onchange=e=>{const n=Math.max(1,Math.min(pages.length,Number(e.target.value)||1));currentId=pages[n-1]?.id||currentId;renderAll()};
  $('#zoomIn').onclick=()=>{scale=Math.min(3,scale*1.15);updateControls();renderMainPage()};
  $('#zoomOut').onclick=()=>{scale=Math.max(.2,scale/1.15);updateControls();renderMainPage()};
  $('#fitPage').onclick=()=>fitPage(true);
  $('#moveUp').onclick=()=>movePage(-1);
  $('#moveDown').onclick=()=>movePage(1);
  $('#deletePage').onclick=deletePage;
  $('#duplicatePage').onclick=duplicatePage;
  $('#rotatePage').onclick=rotatePage;
  $('#clearAnnotations').onclick=clearAnnotations;
  $('#exportTop').onclick=exportPdf;
  $('#undoTop').onclick=undo;
  $('#redoTop').onclick=redo;

  window.addEventListener('keydown',e=>{
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();e.shiftKey?redo():undo()}
    else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='y'){e.preventDefault();redo()}
  });
  window.addEventListener('resize',()=>{ if(pdf) clearTimeout(window.__pdfResizeTimer); window.__pdfResizeTimer=setTimeout(()=>pdf&&fitPage(true),180); });

  applyLanguage();
  updateControls();
  report('page_view');
})();
