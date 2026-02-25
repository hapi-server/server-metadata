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

function combineLinks (columnString, links, split, wrapperClass) {
  if (!wrapperClass) {
    wrapperClass = ''
  }
  return `${columnString}${split}<span class="${wrapperClass}"><nobr>${links.join('')}</nobr></span>`
}

renderFunctions.renderAll = function (columnName, config) {
  return (columnString, type, row, meta) => {
    if (type !== 'display') {
      return columnString
    }
    const constrainedSearch = columnName.endsWith('Date') ||
                              columnName === 'x_nParams' ||
                              columnName === 'length'
    const links = []
    let split = ''
    let wrapperClass = ''
    if (columnName === 'server') {
      const q = { server: columnString }
      links.push(viewLink(q, columnString))
    } else if (columnName === 'dataset') {
      const columnNames = config.dataTables.columns.map(c => c.name)
      const q = {
        server: row[columnNames.indexOf('server')],
        dataset: row[columnNames.indexOf('dataset')]
      }
      links.push(viewLink(q, columnString))
    } else if (columnName === 'parameter') {
      const columnNames = config.dataTables.columns.map(c => c.name)
      const q = {
        server: row[columnNames.indexOf('server')],
        dataset: row[columnNames.indexOf('dataset')],
        parameters: row[columnNames.indexOf('parameter')]
      }
      links.push(viewLink(q, columnString))
    } else if (constrainedSearch) {
      let wrapperClass = 'timeSearchConstraints'
      split = '<br>'
      if (columnString !== '') {
        links.push(searchLink(columnName, columnString, '='))
        links.push('&hairsp;' + searchLink(columnName, columnString, '>'))
        links.push('&hairsp;' + searchLink(columnName, columnString, '≥'))
        links.push('&hairsp;' + searchLink(columnName, columnString, '<'))
        links.push('&hairsp;' + searchLink(columnName, columnString, '≤'))
      }
    }
    if (columnString.startsWith('spase')) {
      const url = columnString.replace('spase://', 'http://spase-metadata.org/')
      let shortID = columnString.split('/')
      shortID = shortID[shortID.length - 1]
      columnString = `<a href="${url}" title="${url}" target="_blank">${shortID}</a>`
    }
    if (links.length > 0) {
      columnString = combineLinks(columnString, links, split, wrapperClass)
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
      .replace(", '...', ", ',<br>&nbsp;&hellip;<br>&nbsp;')
    const style = 'margin: auto; width:80%;text-align:left'
    return `<div style="${style}">${binsSplit}</div>`
  }
}
