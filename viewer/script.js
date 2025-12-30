let mergedData = [];
let ownedUmas = JSON.parse(localStorage.getItem('ownedUmas') || '{}');
let teamSelection = JSON.parse(localStorage.getItem('teamSelection') || '{"Sprint":[], "Mile":[], "Medium":[], "Long":[], "Dirt":[]}');

async function loadData() {
    try {
        const response = await fetch('final_data.json');
        mergedData = await response.json();

        renderTable(mergedData);
        renderTeam();
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

function getBaseName(name) {
    if (!name) return "";
    return name.split(' [')[0].split(' (')[0].trim();
}

function isInTeam(name) {
    for (const cat in teamSelection) {
        if (teamSelection[cat].includes(name)) {
            return true;
        }
    }
    return false;
}

function renderTable(data) {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';

    data.forEach(item => {
        const tr = document.createElement('tr');
        const isOwned = ownedUmas[item.name] || false;
        if (isOwned) tr.classList.add('owned');

        // Escape description for safe HTML embedding
        const escapedDesc = item.description
            ? item.description.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/\n/g, '<br>')
            : '';
        const hasDescription = item.description && item.description.trim().length > 0;

        tr.innerHTML = `
            <td><input type="checkbox" class="owned-checkbox" ${isOwned ? 'checked' : ''} onchange="toggleOwn('${item.name.replace(/'/g, "\\'")}', this)"></td>
            <td>
                <select class="team-select" onchange="addToTeam('${item.name.replace(/'/g, "\\'")}', this.value); this.value=''">
                    <option value="">+ Add</option>
                    <option value="Sprint">Sprint</option>
                    <option value="Mile">Mile</option>
                    <option value="Medium">Medium</option>
                    <option value="Long">Long</option>
                    <option value="Dirt">Dirt</option>
                </select>
            </td>
            <td class="uma-name-cell">
                <strong>${item.name}</strong>
                ${hasDescription ? `<span class="info-icon" data-name="${item.name.replace(/"/g, '&quot;')}">i</span>` : ''}
                ${hasDescription ? `<div class="uma-tooltip" id="tooltip-${item.name.replace(/[^a-zA-Z0-9]/g, '_')}">${escapedDesc}</div>` : ''}
            </td>
            <td><span class="star-indicator">${item.variant || '-'}</span></td>
            <td>${renderTags(item.innate_distance, 'distance-tag')}</td>
            <td>${renderTags(item.innate_style, 'style-tag')}</td>
            <td>${formatStyleReviews(item.style_reviews)}</td>
            <td>${formatReviewBadge(item.trials, 'trials')}</td>
            <td>${formatReviewBadge(item.parent, 'parent')}</td>
            <td>${formatDebuffBadge(item.debuffer)}</td>
            <td>${formatRating(item.lv2)}</td>
            <td>${formatRating(item.lv3)}</td>
            <td>${formatRating(item.lv4)}</td>
            <td>${formatRating(item.lv5)}</td>
        `;
        tbody.appendChild(tr);
    });

    // Add hover and click listeners for info icons
    document.querySelectorAll('.info-icon').forEach(icon => {
        const tooltip = icon.nextElementSibling;
        if (!tooltip || !tooltip.classList.contains('uma-tooltip')) return;

        // Show on hover
        icon.addEventListener('mouseenter', () => {
            if (!tooltip.classList.contains('pinned')) {
                tooltip.classList.add('visible');
            }
        });

        // Hide on mouse leave (unless pinned)
        icon.addEventListener('mouseleave', () => {
            if (!tooltip.classList.contains('pinned')) {
                tooltip.classList.remove('visible');
            }
        });

        // Click to pin/unpin
        icon.addEventListener('click', (e) => {
            e.stopPropagation();
            const isPinned = tooltip.classList.contains('pinned');

            // Close all other tooltips first
            document.querySelectorAll('.uma-tooltip.pinned').forEach(t => {
                t.classList.remove('pinned');
                t.classList.remove('visible');
            });

            if (!isPinned) {
                tooltip.classList.add('pinned');
                tooltip.classList.add('visible');
            }
        });
    });
}



function renderTags(tags, className) {
    if (!tags || tags.length === 0) return '';
    return `<div class="tag-container">
        ${tags.map(t => `<span class="tag ${className}">${t}</span>`).join('')}
    </div>`;
}

function formatReviewBadge(data, type) {
    if (!data || !data.score) return '<span class="rating-badge rating-null">-</span>';

    let info = data.distance || data.style || data.note || '';
    if (data.distance && data.style) info = `${data.distance} ${data.style}`;

    const score = data.score;
    // Extract first digit to handle scores like "5?", "2~3", etc.
    const numScore = parseInt(String(score).match(/\d/)?.[0] || '0');
    // Use same color gradient as awakening levels
    const badgeClass = `rating-${Math.min(Math.max(numScore, 1), 5)}`;

    return `
        <div class="rating-badge ${badgeClass} type-${type}">
            <div class="rating-score">${score}</div>
            ${info ? `<div class="rating-info">${info}</div>` : ''}
        </div>
    `;
}



function formatDebuffBadge(debuff) {
    if (!debuff || (!debuff.type && !debuff.effect)) return '<span class="rating-badge rating-null">-</span>';

    const effect = debuff.effect || '✓';
    const note = debuff.note || '';

    return `
        <div class="rating-badge rating-4 type-debuff">
            <div class="rating-score">${effect}</div>
            <div class="rating-info">${debuff.type || 'Debuff'}${note ? `<br><span class="rating-extra-note">${note}</span>` : ''}</div>
        </div>
    `;
}

function formatStyleReviews(styles) {
    if (!styles || styles.length === 0) return '<span class="rating-badge rating-null">-</span>';
    return `<div class="tag-container style-reviews-container">
        ${styles.map(s => {
        const numScore = parseInt(String(s.score).match(/\d/)?.[0] || '0');
        const badgeClass = `rating-${Math.min(Math.max(numScore, 1), 5)}`;
        // Show short prefix for the type to save space
        const shortType = s.type.split(' ')[0];
        return `<div class="style-review-mini ${badgeClass}" title="${s.type}: ${s.score}">
                <span class="style-score">${s.score}</span>
                <span class="style-type">${shortType}</span>
            </div>`;
    }).join('')}
    </div>`;
}

function formatRating(ratingObj) {
    if (!ratingObj || !ratingObj.score) return '<span class="rating-badge rating-null">-</span>';

    const score = ratingObj.score;
    const numScore = parseInt(score);

    // Check if there's a special annotation (style, track_type, or special_score)
    const hasSpecial = ratingObj.style || ratingObj.track_type || ratingObj.special_score;

    // Color gradient: rating-1 (red) → rating-5 (green), rating-special (cyan) for notes
    let badgeClass = hasSpecial ? 'rating-special' : `rating-${Math.min(Math.max(numScore, 1), 5)}`;

    if (ratingObj.special_score) {
        return `
            <div class="rating-badge ${badgeClass}">
                <div class="rating-score">${score} → ${ratingObj.special_score}</div>
                <div class="rating-info">${ratingObj.special_style}</div>
            </div>
        `;
    }

    let infoHtml = '';
    if (ratingObj.track_type && ratingObj.style) {
        infoHtml = `${ratingObj.track_type} ${ratingObj.style}`;
    } else if (ratingObj.track_type || ratingObj.style) {
        infoHtml = ratingObj.track_type || ratingObj.style;
    }

    return `
        <div class="rating-badge ${badgeClass}">
            <div class="rating-score">${score}</div>
            ${infoHtml ? `<div class="rating-info">${infoHtml}</div>` : ''}
        </div>
    `;
}


// Team Planner Logic
function getUmaData(name) {
    return mergedData.find(uma => uma.name === name);
}

function getStyleAbbrev(style) {
    if (!style) return '?';
    const abbrevs = {
        'Front Runner': 'FR',
        'Pace Chaser': 'PC',
        'Late Surger': 'LS',
        'End Closer': 'EC'
    };
    return abbrevs[style] || style.substring(0, 2);
}

function getStyleClass(style) {
    if (!style) return 'style-unknown';
    return 'style-' + style.toLowerCase().replace(/\s+/g, '-');
}

function renderTeam() {
    const categories = ['Sprint', 'Mile', 'Medium', 'Long', 'Dirt'];
    categories.forEach(cat => {
        const container = document.getElementById(`slots-${cat}`);
        container.innerHTML = '';

        const slots = teamSelection[cat] || [];
        const styleCounts = {};
        
        for (let i = 0; i < 3; i++) {
            const slot = document.createElement('div');
            slot.className = 'team-slot';
            if (slots[i]) {
                const umaData = getUmaData(slots[i]);
                const style = umaData?.trials?.style || umaData?.innate_style?.[0] || null;
                const styleAbbrev = getStyleAbbrev(style);
                const styleClass = getStyleClass(style);
                
                // Count styles for summary
                if (style) {
                    styleCounts[style] = (styleCounts[style] || 0) + 1;
                }
                
                slot.innerHTML = `
                    <span class="remove-btn" onclick="removeFromTeam('${cat}', ${i})">×</span>
                    <strong>${slots[i]}</strong>
                    <span class="slot-style ${styleClass}">${styleAbbrev}</span>
                `;
                slot.classList.add('filled');
            } else {
                slot.innerHTML = `<span class="empty-text">Empty</span>`;
            }
            container.appendChild(slot);
        }
        
        // Update style summary for this category
        const categoryEl = container.closest('.team-category');
        let summaryEl = categoryEl.querySelector('.style-summary');
        if (!summaryEl) {
            summaryEl = document.createElement('div');
            summaryEl.className = 'style-summary';
            categoryEl.appendChild(summaryEl);
        }
        
        if (Object.keys(styleCounts).length > 0) {
            const summaryHtml = Object.entries(styleCounts)
                .map(([style, count]) => `<span class="style-count ${getStyleClass(style)}">${getStyleAbbrev(style)}×${count}</span>`)
                .join('');
            summaryEl.innerHTML = summaryHtml;
        } else {
            summaryEl.innerHTML = '';
        }
    });
}

function addToTeam(name, category) {
    if (!category) return;
    const baseName = getBaseName(name);

    for (const cat in teamSelection) {
        if (teamSelection[cat].some(n => getBaseName(n) === baseName)) {
            alert(`Duplicate character: ${baseName} is already in the team!`);
            return;
        }
    }

    if (teamSelection[category].length >= 3) {
        alert(`${category} category is full! (Max 3)`);
        return;
    }

    teamSelection[category].push(name);
    localStorage.setItem('teamSelection', JSON.stringify(teamSelection));
    renderTeam();
}

function removeFromTeam(category, index) {
    teamSelection[category].splice(index, 1);
    localStorage.setItem('teamSelection', JSON.stringify(teamSelection));
    renderTeam();
}

function toggleOwn(name, checkbox) {
    ownedUmas[name] = checkbox.checked;
    localStorage.setItem('ownedUmas', JSON.stringify(ownedUmas));

    const row = checkbox.closest('tr');
    if (checkbox.checked) {
        row.classList.add('owned');
    } else {
        row.classList.remove('owned');
    }
}

// Search Functionality
document.getElementById('search-input').addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase().trim();
    if (!term) {
        renderTable(mergedData);
        return;
    }

    const filtered = mergedData.filter(item => {
        const name = item.name.toLowerCase();
        const variant = (item.variant || "").toLowerCase();
        const fullName = `${name} [${variant}]`;

        return name.includes(term) || variant.includes(term) || fullName.includes(term);
    });
    renderTable(filtered);
});

// Sort Functionality
let sortConfig = { key: null, direction: 'asc' };

document.querySelectorAll('th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const key = th.dataset.sort;
        if (sortConfig.key === key) {
            sortConfig.direction = sortConfig.direction === 'asc' ? 'desc' : 'asc';
        } else {
            sortConfig.key = key;
            sortConfig.direction = 'asc';
        }

        sortData(key, sortConfig.direction);
    });
});

function sortData(key, direction) {
    const sorted = [...mergedData].sort((a, b) => {
        let valA, valB;

        if (key === 'owned') {
            valA = ownedUmas[a.name] ? 1 : 0;
            valB = ownedUmas[b.name] ? 1 : 0;
        } else if (key === 'name') {
            valA = a.name.toLowerCase();
            valB = b.name.toLowerCase();
        } else if (key === 'variant') {
            valA = (a.variant || "").toLowerCase();
            valB = (b.variant || "").toLowerCase();
        } else if (['trials', 'parent', 'debuffer'].includes(key)) {
            valA = parseFloat(a[key]?.score || a[key]?.effect) || 0;
            valB = parseFloat(b[key]?.score || b[key]?.effect) || 0;
        } else {
            // Awakening ratings
            const objA = a[key];
            const objB = b[key];
            valA = objA ? (parseInt(objA.score) || 0) : 0;
            valB = objB ? (parseInt(objB.score) || 0) : 0;
        }

        if (valA < valB) return direction === 'asc' ? -1 : 1;
        if (valA > valB) return direction === 'asc' ? 1 : -1;
        return 0;
    });
    renderTable(sorted);
}

// Filter Logic - Custom Dropdown
function getCheckedValues(filterName) {
    const dropdown = document.querySelector(`[data-filter="${filterName}"]`);
    if (!dropdown) return [];
    return Array.from(dropdown.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
}

function updateDropdownLabel(filterName) {
    const dropdown = document.querySelector(`[data-filter="${filterName}"]`);
    if (!dropdown) return;
    const selected = Array.from(dropdown.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
    const labelSpan = dropdown.querySelector('.count');

    if (selected.length === 0) {
        labelSpan.textContent = '';
    } else if (selected.length <= 2) {
        labelSpan.textContent = `: ${selected.join(', ')}`;
    } else {
        labelSpan.textContent = `: ${selected[0]}, ${selected[1]} +${selected.length - 2}`;
    }
}

function applyFilters() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase().trim();
    const distanceFilters = getCheckedValues('distance');
    const styleFilters = getCheckedValues('style');
    const trialsFilters = getCheckedValues('trials');
    const parentFilters = getCheckedValues('parent');
    const debuffFilter = document.getElementById('filter-debuff').value;
    const ownedFilter = document.getElementById('filter-owned')?.value || '';
    const inTeamFilter = document.getElementById('filter-in-team')?.value || '';



    let filtered = mergedData.filter(item => {
        // Search filter
        if (searchTerm) {
            const name = item.name.toLowerCase();
            const variant = (item.variant || "").toLowerCase();
            const fullName = `${name} [${variant}]`;
            if (!name.includes(searchTerm) && !variant.includes(searchTerm) && !fullName.includes(searchTerm)) {
                return false;
            }
        }

        // Distance filter (any match)
        if (distanceFilters.length > 0) {
            const itemDistances = item.innate_distance || [];
            if (!distanceFilters.some(d => itemDistances.includes(d))) {
                return false;
            }
        }

        // Style filter (any match)
        if (styleFilters.length > 0) {
            const itemStyles = item.innate_style || [];
            if (!styleFilters.some(s => itemStyles.includes(s))) {
                return false;
            }
        }

        // Trials score filter
        if (trialsFilters.length > 0) {
            const trialsScore = item.trials?.score ? String(parseInt(item.trials.score)) : null;
            if (!trialsScore || !trialsFilters.includes(trialsScore)) {
                return false;
            }
        }

        // Parent score filter
        if (parentFilters.length > 0) {
            const parentScore = item.parent?.score ? String(parseInt(item.parent.score)) : null;
            if (!parentScore || !parentFilters.includes(parentScore)) {
                return false;
            }
        }

        // Debuff filter
        if (debuffFilter === 'yes') {
            if (!item.debuffer || (!item.debuffer.type && !item.debuffer.effect)) {
                return false;
            }
        } else if (debuffFilter === 'no') {
            if (item.debuffer && (item.debuffer.type || item.debuffer.effect)) {
                return false;
            }
        }

        // Owned filter
        if (ownedFilter === 'yes' && !ownedUmas[item.name]) {
            return false;
        } else if (ownedFilter === 'no' && ownedUmas[item.name]) {
            return false;
        }

        // In Team filter
        if (inTeamFilter === 'yes' && !isInTeam(item.name)) {
            return false;
        } else if (inTeamFilter === 'no' && isInTeam(item.name)) {
            return false;
        }

        return true;
    });

    renderTable(filtered);
}


// Dropdown toggle behavior
document.querySelectorAll('.dropdown-filter .dropdown-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const dropdown = btn.closest('.dropdown-filter');
        const wasOpen = dropdown.classList.contains('open');

        // Close all dropdowns first
        document.querySelectorAll('.dropdown-filter').forEach(d => d.classList.remove('open'));

        // Toggle the clicked one
        if (!wasOpen) dropdown.classList.add('open');
    });
});

// Close dropdowns and tooltips when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown-filter')) {
        document.querySelectorAll('.dropdown-filter').forEach(d => d.classList.remove('open'));
    }
    if (!e.target.closest('.uma-tooltip') && !e.target.closest('.info-icon')) {
        document.querySelectorAll('.uma-tooltip.pinned').forEach(t => {
            t.classList.remove('pinned');
            t.classList.remove('visible');
        });
    }
});

// Checkbox change listeners
document.querySelectorAll('.dropdown-filter input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', () => {
        const filterName = cb.closest('.dropdown-filter').dataset.filter;
        updateDropdownLabel(filterName);
        applyFilters();
    });
});

// Debuff filter listener
document.getElementById('filter-debuff').addEventListener('change', applyFilters);

// Owned filter listener
document.getElementById('filter-owned')?.addEventListener('change', applyFilters);

// In Team filter listener
document.getElementById('filter-in-team')?.addEventListener('change', applyFilters);

// Search listener
document.getElementById('search-input').addEventListener('input', applyFilters);

// Clear filters button
document.getElementById('clear-filters').addEventListener('click', () => {
    document.getElementById('search-input').value = '';
    document.querySelectorAll('.dropdown-filter input[type="checkbox"]').forEach(cb => cb.checked = false);
    document.querySelectorAll('.dropdown-filter .count').forEach(span => span.textContent = '');
    document.getElementById('filter-debuff').value = '';
    document.getElementById('filter-owned').value = '';
    document.getElementById('filter-in-team').value = '';
    applyFilters();
});



// Data Export/Import for port migration
function exportData() {
    const data = {
        ownedUmas: ownedUmas,
        teamSelection: teamSelection
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'team-planner-backup.json';
    a.click();
    URL.revokeObjectURL(url);
}

function importData() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const data = JSON.parse(event.target.result);
                if (data.ownedUmas) {
                    ownedUmas = data.ownedUmas;
                    localStorage.setItem('ownedUmas', JSON.stringify(ownedUmas));
                }
                if (data.teamSelection) {
                    teamSelection = data.teamSelection;
                    localStorage.setItem('teamSelection', JSON.stringify(teamSelection));
                }
                renderTable(mergedData);
                renderTeam();
                alert('Data imported successfully!');
            } catch (err) {
                alert('Error importing data: ' + err.message);
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

loadData();
