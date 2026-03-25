function viewLink (q, columnString) {
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


renderFunctions.renderAll = function (columnName, config) {
  return (columnString, type, row, meta) => {
    if (type !== 'display') {
      return columnString
    }

    if (columnName === 'server') {
      const q = { server: columnString }
      return renderFunctions._combineLinks(columnString, viewLink(q, columnString))
    } else if (columnName === 'dataset') {
      const columnNames = config.dataTables.columns.map(c => c.name)
      const q = {
        server: row[columnNames.indexOf('server')],
        dataset: row[columnNames.indexOf('dataset')]
      }
      return renderFunctions._combineLinks(columnString, viewLink(q, columnString))
    } else if (columnName === 'parameter') {
      const columnNames = config.dataTables.columns.map(c => c.name)
      const q = {
        server: row[columnNames.indexOf('server')],
        dataset: row[columnNames.indexOf('dataset')],
        parameters: row[columnNames.indexOf('parameter')]
      }
      return renderFunctions._combineLinks(columnString, viewLink(q, columnString))
    } else {
      return columnString
    }
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
      .replace(", '...', ", ',<br>&nbsp;&hellip;<br>&nbsp;')
    const style = 'margin: auto; width:80%;text-align:left'
    return `<div style="${style}">${binsSplit}</div>`
  }
}
