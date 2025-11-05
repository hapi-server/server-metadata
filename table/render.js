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
function triggerSearch (columnName, searchValue) {
  const e = $.Event('keydown')
  e.which = 13
  e.keyCode = 13
  const el = `.dataTables_scrollHead input.columnSearch[name=${columnName}]`
  $(el).trigger('input')
  $(el).val(searchValue).trigger(e)
}

function searchLink (columnName, columnString, constraint) {
  const constraintIcon = constraint || '🔍'
  if (!constraint || constraint === '=') {
    constraint = ''
  }
  let attrs = 'title="Search column for this exact value"'
  if (constraint !== '') {
    attrs = `title="Search columns for datetimes ${constraint} ${columnString}"`
  }
  attrs += ' style="text-decoration:none;"'
  attrs += ` onclick="triggerSearch('${columnName}', '${columnString}')"`
  const url = `#${columnName}=${constraint}${columnString}`
  const link = `<a href="${url}" ${attrs}>${constraintIcon}</a>`
  return link
}
function combineLinks (columnString, links) {
  return `${columnString}&hairsp;<nobr>${links.join('')}</nobr>`
}

renderFunctions.renderAll = function (columnName, config) {
  return (columnString, type, row, meta) => {
    if (type !== 'display') {
      return columnString
    }
    const links = []
    if (columnName === 'server') {
      const q = { server: columnString }
      links.push(viewLink(q, columnString))
      links.push(searchLink(columnName, columnString))
    } else if (columnName === 'dataset') {
      const columnNames = config.dataTables.columns.map(c => c.name)
      const q = {
        server: row[columnNames.indexOf('server')],
        dataset: row[columnNames.indexOf('dataset')]
      }
      links.push(viewLink(q, columnString))
      links.push(searchLink(columnName, columnString))
    } else if (columnName === 'parameter') {
      const columnNames = config.dataTables.columns.map(c => c.name)
      const q = {
        server: row[columnNames.indexOf('server')],
        dataset: row[columnNames.indexOf('dataset')],
        parameters: row[columnNames.indexOf('parameter')]
      }
      links.push(viewLink(q, columnString))
      links.push(searchLink(columnName, columnString))
    } else if (columnName === 'title') {
      const columnStringOriginal = columnString
      columnString = renderFunctions.ellipsis(columnName, config, 30)(columnString, type, row, meta)
      links.push(searchLink(columnName, columnStringOriginal))
    } else if (columnName === 'description') {
      const columnStringOriginal = columnString
      columnString = renderFunctions.ellipsis(columnName, config, 50)(columnString, type, row, meta)
      links.push(searchLink(columnName, columnStringOriginal))
    } else if (columnName.endsWith('Date')) {
      links.push(searchLink(columnName, columnString, '='))
      links.push('&hairsp;' + searchLink(columnName, columnString, '>'))
      links.push('&hairsp;' + searchLink(columnName, columnString, '≥'))
      links.push('&hairsp;' + searchLink(columnName, columnString, '<'))
      links.push('&hairsp;' + searchLink(columnName, columnString, '≤'))
    } else {
      links.push(searchLink(columnName, columnString))
    }
    if (links.length > 0) {
      columnString = combineLinks(columnString, links)
    }
    return columnString
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
