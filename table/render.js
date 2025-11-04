function viewLink (q, columnString, type) {
  let viewURL = `https://hapi-server.org/servers/#server=${q.server}`
  if (q.dataset) {
    viewURL += `&dataset=${q.dataset}`
  }
  if (q.parameters) {
    viewURL += `&parameters=${q.parameters}`
  }

  const span = '<span class="open-in-new-tab"></span>'
  const attrs = `href="${viewURL}" title="View in HAPI Data Explorer"`
  const link = `<a ${attrs} target="_blank">${span}</a>`
  return link
}
function searchLink (columnName, columnString) {
  const url = `#${columnName}=${columnString}`
  const attrs = `href="${url}" title="Search Column for this Value"`
  const link = `<a ${attrs} target="_blank">${columnString}</a>`
  return link
}

renderFunctions.renderServer = function (columnName, config) {
  return (columnString, type, row, meta) => {
    if (type !== 'display') {
      return columnString
    }
    const q = { server: columnString }
    let links = searchLink('server', columnString)
    links += viewLink(q, columnString, 'renderLink')
    return links
  }
}
renderFunctions.renderID = function (columnName, config) {
  return (columnString, type, row, meta) => {
    if (type !== 'display') {
      return columnString
    }
    const columnNames = config.dataTables.columns.map(c => c.name)
    const server = row[columnNames.indexOf('server')]
    const dataset = row[columnNames.indexOf('id')]
    const q = { server, dataset }
    let links = searchLink('id', columnString)
    links += viewLink(q, columnString, 'renderLink')
    return links
  }
}
renderFunctions.renderName = function (columnName, config) {
  return (columnString, type, row, meta) => {
    if (type !== 'display') {
      return columnString
    }
    const columnNames = config.dataTables.columns.map(c => c.name)
    const server = row[columnNames.indexOf('server')]
    const dataset = row[columnNames.indexOf('id')]
    const parameters = row[columnNames.indexOf('name')]
    const q = { server, dataset, parameters }
    let links = searchLink('name', columnString)
    links += viewLink(q, columnString, 'renderLink')
    return links
  }
}
renderFunctions.renderBins = function (columnName, config) {
  return (columnString, type, row, meta) => {
    if (type !== 'display') {
      return columnString
    }
    const binsSplit =
    columnString
      .replaceAll('], [', '],<br>&nbsp;[')
      .replace(", '...', ", ",<br>&nbsp;&hellip;<br>&nbsp;")
    return `<div style="text-align:left">${binsSplit}</div>`
  }
}
