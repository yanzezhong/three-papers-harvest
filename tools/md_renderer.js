function md(src){
  let t=src.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  const lines=t.split("\n");const out=[];let i=0;
  const inl=s=>s
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g,'<img src="$2" alt="$1" style="max-width:100%;border-radius:8px">')
    .replace(/`([^`]+)`/g,"<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>")
    .replace(/\*([^*\n]+)\*/g,"<em>$1</em>")
    .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
  while(i<lines.length){
    let Ln=lines[i];
    if(/^\s*$/.test(Ln)){i++;continue;}
    const h=Ln.match(/^(#{1,4})\s+(.*)/);
    if(h){out.push(`<h${h[1].length}>${inl(h[2])}</h${h[1].length}>`);i++;continue;}
    if(/^(-{3,}|\*{3,})\s*$/.test(Ln)){out.push("<hr>");i++;continue;}
    if(/^(>|&gt;)\s?/.test(Ln)){const buf=[];while(i<lines.length&&/^(>|&gt;)\s?/.test(lines[i])){buf.push(lines[i].replace(/^(>|&gt;)\s?/,""));i++;}out.push(`<blockquote>${inl(buf.join(" "))}</blockquote>`);continue;}
    if(/^[-*]\s+/.test(Ln)){const buf=[];while(i<lines.length&&/^[-*]\s+/.test(lines[i])){buf.push(`<li>${inl(lines[i].replace(/^[-*]\s+/,""))}</li>`);i++;}out.push(`<ul>${buf.join("")}</ul>`);continue;}
    if(/^\d+\.\s+/.test(Ln)){const buf=[];while(i<lines.length&&/^\d+\.\s+/.test(lines[i])){buf.push(`<li>${inl(lines[i].replace(/^\d+\.\s+/,""))}</li>`);i++;}out.push(`<ol>${buf.join("")}</ol>`);continue;}
    const buf=[Ln];i++;
    while(i<lines.length&&!/^\s*$/.test(lines[i])&&!/^(#{1,4}\s|>|[-*]\s|\d+\.\s|-{3,})/.test(lines[i])){buf.push(lines[i]);i++;}
    out.push(`<p>${inl(buf.join(" ").replace(/^\s+|\s+$/g,""))}</p>`);
  }
  return out.join("\n").replace(/^<h1>[^<]*<\/h1>\s*/,"");
}
