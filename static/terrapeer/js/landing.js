(() => {
    const r = document.getElementById('tp-garden-home'),
        q = s => r.querySelector(s),
        qa = s => [...r.querySelectorAll(s)];
    q('.gh-grid').append(q('#gh-journal'), q('#gh-plan'));
    const assets = {
        tomato: '/static/terrapeer/img/landing-c3b47fd982ed.png',
        mint: '/static/terrapeer/img/landing-2644e992c81a.png',
        sprout: '/static/terrapeer/img/landing-29bdd9e458dd.png',
        unchecked: '/static/terrapeer/img/landing-1b11971c51e7.png',
        checked: '/static/terrapeer/img/landing-579b9e006174.png'
    };
    const plants = [{
        id: 'tomato',
        name: 'Tomato',
        pot: 'Pot A',
        stage: 'Fruiting',
        status: 'Active',
        start: '2026-09-20',
        source: 'Balcony Plan',
        image: assets.tomato
    }, {
        id: 'mint',
        name: 'Peppermint',
        pot: 'Pot B',
        stage: 'Growing',
        status: 'Active',
        start: '2026-09-20',
        source: 'Existing plant',
        image: assets.mint
    }];
    const tasks = [{
        id: 1,
        plant: 'mint',
        title: 'Check soil moisture',
        date: '2026-10-21',
        time: '08:00',
        done: false
    }, {
        id: 2,
        plant: 'tomato',
        title: 'Inspect the plant support',
        date: '2026-10-21',
        time: '16:00',
        done: false
    }, {
        id: 3,
        plant: 'mint',
        title: 'Check leaf condition',
        date: '2026-10-22',
        time: '09:00',
        done: false
    }, {
        id: 4,
        plant: 'tomato',
        title: 'Observe fruit development',
        date: '2026-10-24',
        time: '08:00',
        done: false
    }];
    let spaceData = {
            name: 'My Balcony',
            kind: 'Balcony',
            location: 'Depok, Indonesia',
            light: '4–6',
            rain: 'Exposed',
            support: 'Yes',
            care: 'Daily',
            notes: ''
        },
        potData = {
            pot: 'Pot C',
            name: 'Pot C',
            width: '30',
            depth: '30',
            capacity: '15',
            drainage: 'With holes'
        },
        planData = {
            name: 'Balcony Plan',
            status: 'Draft',
            notes: ''
        },
        profileData = {
            name: 'Nashri'
        };
    const plans = [{
        id: 'chilli',
        name: 'Chilli',
        pot: 'Pot C',
        planted: false
    }, {
        id: 'basil',
        name: 'Basil',
        pot: 'Pot D',
        planted: false
    }];
    let entries = [{
        id: 1,
        plant: 'mint',
        type: 'Growth',
        note: 'New leaves appeared',
        date: '2026-10-20',
        condition: 'Healthy'
    }, {
        id: 2,
        plant: 'tomato',
        type: 'Fruiting',
        note: 'The first fruits are here',
        date: '2026-10-11',
        condition: 'Healthy'
    }];
    const stages = ['Planted', 'Growing', 'Flowering', 'Fruiting', 'Harvesting', 'Finished'];
    let selectedDate = '2026-10-21',
        weekOffset = 0,
        filter = 'pending',
        action = '',
        editId = null,
        auto = false,
        timer = null,
        deleteArmed = false;
    const esc = s => String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    } [c]));
    const icon = n => '<i data-lucide="' + n + '" aria-hidden="true"></i>';
    const originalIcons = {
        "cloud-sun": "<svg aria-hidden=\"true\" data-tp-original=\"10\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n<path d=\"M11 5V1H13V5H11ZM17.65 7.75L16.25 6.35L19.075 3.5L20.475 4.925L17.65 7.75ZM19 13V11H23V13H19ZM19.075 20.475L16.25 17.65L17.65 16.25L20.5 19.05L19.075 20.475ZM6.35 7.75L3.525 4.925L4.95 3.5L7.75 6.35L6.35 7.75ZM6 19H10.5C10.9167 19 11.2708 18.8542 11.5625 18.5625C11.8542 18.2708 12 17.9167 12 17.5C12 17.0833 11.8583 16.7292 11.575 16.4375C11.2917 16.1458 10.9417 16 10.525 16H9.25L8.75 14.8C8.51667 14.25 8.15 13.8125 7.65 13.4875C7.15 13.1625 6.6 13 6 13C5.16667 13 4.45833 13.2917 3.875 13.875C3.29167 14.4583 3 15.1667 3 16C3 16.8333 3.29167 17.5417 3.875 18.125C4.45833 18.7083 5.16667 19 6 19ZM6 21C4.61667 21 3.4375 20.5125 2.4625 19.5375C1.4875 18.5625 1 17.3833 1 16C1 14.6167 1.4875 13.4375 2.4625 12.4625C3.4375 11.4875 4.61667 11 6 11C7 11 7.9125 11.2708 8.7375 11.8125C9.5625 12.3542 10.175 13.0833 10.575 14C11.5417 14 12.3542 14.3583 13.0125 15.075C13.6708 15.7917 14 16.65 14 17.65C13.9667 18.6 13.6125 19.3958 12.9375 20.0375C12.2625 20.6792 11.45 21 10.5 21H6ZM14 17.65C13.9167 17.3167 13.8333 16.9917 13.75 16.675C13.6667 16.3583 13.5833 16.0333 13.5 15.7C14.25 15.3833 14.8542 14.8917 15.3125 14.225C15.7708 13.5583 16 12.8167 16 12C16 10.9 15.6083 9.95833 14.825 9.175C14.0417 8.39167 13.1 8 12 8C11 8 10.125 8.325 9.375 8.975C8.625 9.625 8.18333 10.45 8.05 11.45C7.71667 11.3667 7.375 11.2917 7.025 11.225C6.675 11.1583 6.33333 11.0833 6 11C6.23333 9.53333 6.92083 8.33333 8.0625 7.4C9.20417 6.46667 10.5167 6 12 6C13.6667 6 15.0833 6.58333 16.25 7.75C17.4167 8.91667 18 10.3333 18 12C18 13.2833 17.6333 14.4375 16.9 15.4625C16.1667 16.4875 15.2 17.2167 14 17.65Z\" fill=\"currentColor\"/>\n</svg>\n",
        "cloud-rain": "<svg aria-hidden=\"true\" data-tp-original=\"8\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n<path d=\"M13.95 21.9C13.7 22.0333 13.4458 22.0542 13.1875 21.9625C12.9292 21.8708 12.7333 21.7 12.6 21.45L11.1 18.45C10.9667 18.2 10.9458 17.9458 11.0375 17.6875C11.1292 17.4292 11.3 17.2333 11.55 17.1C11.8 16.9667 12.0542 16.9458 12.3125 17.0375C12.5708 17.1292 12.7667 17.3 12.9 17.55L14.4 20.55C14.5333 20.8 14.5542 21.0542 14.4625 21.3125C14.3708 21.5708 14.2 21.7667 13.95 21.9ZM19.95 21.9C19.7 22.0333 19.4458 22.0542 19.1875 21.9625C18.9292 21.8708 18.7333 21.7 18.6 21.45L17.1 18.45C16.9667 18.2 16.9458 17.9458 17.0375 17.6875C17.1292 17.4292 17.3 17.2333 17.55 17.1C17.8 16.9667 18.0542 16.9458 18.3125 17.0375C18.5708 17.1292 18.7667 17.3 18.9 17.55L20.4 20.55C20.5333 20.8 20.5542 21.0542 20.4625 21.3125C20.3708 21.5708 20.2 21.7667 19.95 21.9ZM7.95 21.9C7.7 22.0333 7.44583 22.0542 7.1875 21.9625C6.92917 21.8708 6.73333 21.7 6.6 21.45L5.1 18.45C4.96667 18.2 4.94583 17.9458 5.0375 17.6875C5.12917 17.4292 5.3 17.2333 5.55 17.1C5.8 16.9667 6.05417 16.9458 6.3125 17.0375C6.57083 17.1292 6.76667 17.3 6.9 17.55L8.4 20.55C8.53333 20.8 8.55417 21.0542 8.4625 21.3125C8.37083 21.5708 8.2 21.7667 7.95 21.9ZM7.5 16C5.98333 16 4.6875 15.4625 3.6125 14.3875C2.5375 13.3125 2 12.0167 2 10.5C2 9.11667 2.45833 7.90833 3.375 6.875C4.29167 5.84167 5.425 5.23333 6.775 5.05C7.30833 4.1 8.0375 3.35417 8.9625 2.8125C9.8875 2.27083 10.9 2 12 2C13.5 2 14.8042 2.47917 15.9125 3.4375C17.0208 4.39583 17.6917 5.59167 17.925 7.025C19.075 7.125 20.0417 7.6 20.825 8.45C21.6083 9.3 22 10.3167 22 11.5C22 12.75 21.5625 13.8125 20.6875 14.6875C19.8125 15.5625 18.75 16 17.5 16H7.5ZM7.5 14H17.5C18.2 14 18.7917 13.7583 19.275 13.275C19.7583 12.7917 20 12.2 20 11.5C20 10.8 19.7583 10.2083 19.275 9.725C18.7917 9.24167 18.2 9 17.5 9H16V8C16 6.9 15.6083 5.95833 14.825 5.175C14.0417 4.39167 13.1 4 12 4C11.2 4 10.4708 4.21667 9.8125 4.65C9.15417 5.08333 8.65833 5.66667 8.325 6.4L8.075 7H7.45C6.5 7.03333 5.6875 7.3875 5.0125 8.0625C4.3375 8.7375 4 9.55 4 10.5C4 11.4667 4.34167 12.2917 5.025 12.975C5.70833 13.6583 6.53333 14 7.5 14Z\" fill=\"currentColor\"/>\n</svg>\n",
        "droplets": "<svg aria-hidden=\"true\" data-tp-original=\"37\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n<path d=\"M17.5 4C18.6667 5.03333 19.5417 5.9875 20.125 6.8625C20.7083 7.7375 21 8.55 21 9.3C21 10.3 20.6667 11.1667 20 11.9C19.3333 12.6333 18.5 13 17.5 13C16.5 13 15.6667 12.6333 15 11.9C14.3333 11.1667 14 10.3 14 9.3C14 8.6 14.3083 7.78333 14.925 6.85C15.5417 5.91667 16.4 4.96667 17.5 4ZM17.5 6.775C17.05 7.25833 16.6875 7.72917 16.4125 8.1875C16.1375 8.64583 16 9.01667 16 9.3C16 9.75 16.1417 10.1458 16.425 10.4875C16.7083 10.8292 17.0667 11 17.5 11C17.9333 11 18.2917 10.8292 18.575 10.4875C18.8583 10.1458 19 9.75 19 9.3C19 9.01667 18.8625 8.64583 18.5875 8.1875C18.3125 7.72917 17.95 7.25833 17.5 6.775ZM12 22C9.71667 22 7.8125 21.2167 6.2875 19.65C4.7625 18.0833 4 16.1333 4 13.8C4 12.1333 4.6625 10.3208 5.9875 8.3625C7.3125 6.40417 9.31667 4.28333 12 2C12.9 2.76667 13.725 3.51667 14.475 4.25C15.225 4.98333 15.9 5.7 16.5 6.4C16.3833 6.55 16.175 6.83333 15.875 7.25C15.575 7.66667 15.3833 7.94167 15.3 8.075C14.85 7.54167 14.3542 6.9875 13.8125 6.4125C13.2708 5.8375 12.6667 5.25 12 4.65C10.0167 6.46667 8.52083 8.14167 7.5125 9.675C6.50417 11.2083 6 12.5833 6 13.8C6 15.5833 6.56667 17.0625 7.7 18.2375C8.83333 19.4125 10.2667 20 12 20C12.8667 20 13.6667 19.8417 14.4 19.525C15.1333 19.2083 15.7667 18.775 16.3 18.225C16.8333 17.675 17.25 17.0208 17.55 16.2625C17.85 15.5042 18 14.6833 18 13.8C18 13.5167 17.9708 13.2167 17.9125 12.9C17.8542 12.5833 17.7667 12.2583 17.65 11.925C17.8 11.8417 18.0958 11.6833 18.5375 11.45C18.9792 11.2167 19.275 11.0583 19.425 10.975C19.6083 11.4583 19.75 11.9375 19.85 12.4125C19.95 12.8875 20 13.35 20 13.8C20 16.1333 19.2375 18.0833 17.7125 19.65C16.1875 21.2167 14.2833 22 12 22ZM12.275 19C12.475 18.9833 12.6458 18.9042 12.7875 18.7625C12.9292 18.6208 13 18.45 13 18.25C13 18.0167 12.925 17.8292 12.775 17.6875C12.625 17.5458 12.4333 17.4833 12.2 17.5C11.5167 17.55 10.7917 17.3625 10.025 16.9375C9.25833 16.5125 8.775 15.7417 8.575 14.625C8.54167 14.4417 8.45417 14.2917 8.3125 14.175C8.17083 14.0583 8.00833 14 7.825 14C7.59167 14 7.4 14.0875 7.25 14.2625C7.1 14.4375 7.05 14.6417 7.1 14.875C7.38333 16.3917 8.05 17.475 9.1 18.125C10.15 18.775 11.2083 19.0667 12.275 19Z\" fill=\"currentColor\"/>\n</svg>\n",
        "sun": "<svg aria-hidden=\"true\" data-tp-original=\"47\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n<path d=\"M11 5V1H13V5H11ZM17.65 7.75L16.275 6.375L19.075 3.5L20.475 4.925L17.65 7.75ZM19 13V11H23V13H19ZM11 23V19H13V23H11ZM6.35 7.7L3.5 4.925L4.925 3.525L7.75 6.35L6.35 7.7ZM19.05 20.5L16.275 17.625L17.625 16.275L20.475 19.025L19.05 20.5ZM1 13V11H5V13H1ZM4.925 20.5L3.525 19.075L6.325 16.275L7.05 16.95L7.775 17.65L4.925 20.5ZM7.75 16.25C6.58333 15.0833 6 13.6667 6 12C6 10.3333 6.58333 8.91667 7.75 7.75C8.91667 6.58333 10.3333 6 12 6C13.6667 6 15.0833 6.58333 16.25 7.75C17.4167 8.91667 18 10.3333 18 12C18 13.6667 17.4167 15.0833 16.25 16.25C15.0833 17.4167 13.6667 18 12 18C10.3333 18 8.91667 17.4167 7.75 16.25ZM14.825 14.825C15.6083 14.0417 16 13.1 16 12C16 10.9 15.6083 9.95833 14.825 9.175C14.0417 8.39167 13.1 8 12 8C10.9 8 9.95833 8.39167 9.175 9.175C8.39167 9.95833 8 10.9 8 12C8 13.1 8.39167 14.0417 9.175 14.825C9.95833 15.6083 10.9 16 12 16C13.1 16 14.0417 15.6083 14.825 14.825Z\" fill=\"currentColor\"/>\n</svg>\n",
        "flower-2": "<svg aria-hidden=\"true\" data-tp-original=\"17\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n<path d=\"M8.55 20H15.45L16.45 16H7.55L8.55 20ZM8.55 22C8.08333 22 7.675 21.8583 7.325 21.575C6.975 21.2917 6.74167 20.925 6.625 20.475L5.5 16H18.5L17.375 20.475C17.2583 20.925 17.025 21.2917 16.675 21.575C16.325 21.8583 15.9167 22 15.45 22H8.55ZM5 14H19V12H5V14ZM12 8C12 6.33333 12.5833 4.91667 13.75 3.75C14.9167 2.58333 16.3333 2 18 2C18 3.5 17.525 4.8 16.575 5.9C15.625 7 14.4333 7.66667 13 7.9V10H21V14C21 14.55 20.8042 15.0208 20.4125 15.4125C20.0208 15.8042 19.55 16 19 16H5C4.45 16 3.97917 15.8042 3.5875 15.4125C3.19583 15.0208 3 14.55 3 14V10H11V7.9C9.56667 7.66667 8.375 7 7.425 5.9C6.475 4.8 6 3.5 6 2C7.66667 2 9.08333 2.58333 10.25 3.75C11.4167 4.91667 12 6.33333 12 8Z\" fill=\"currentColor\"/>\n</svg>\n",
        "calendar-check": "<svg aria-hidden=\"true\" data-tp-original=\"74\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n<path d=\"M5 21C4.45 21 3.97917 20.8042 3.5875 20.4125C3.19583 20.0208 3 19.55 3 19V5C3 4.45 3.19583 3.97917 3.5875 3.5875C3.97917 3.19583 4.45 3 5 3H9.2C9.41667 2.4 9.77917 1.91667 10.2875 1.55C10.7958 1.18333 11.3667 1 12 1C12.6333 1 13.2042 1.18333 13.7125 1.55C14.2208 1.91667 14.5833 2.4 14.8 3H19C19.55 3 20.0208 3.19583 20.4125 3.5875C20.8042 3.97917 21 4.45 21 5V11.7C20.6833 11.55 20.3583 11.4208 20.025 11.3125C19.6917 11.2042 19.35 11.125 19 11.075V5H5V19H11.05C11.1 19.3667 11.1792 19.7167 11.2875 20.05C11.3958 20.3833 11.525 20.7 11.675 21H5ZM5 18V19V5V11.075V11V18ZM7 17H11.075C11.125 16.65 11.2042 16.3083 11.3125 15.975C11.4208 15.6417 11.5417 15.3167 11.675 15H7V17ZM7 13H13.1C13.6333 12.5 14.2292 12.0833 14.8875 11.75C15.5458 11.4167 16.25 11.1917 17 11.075V11H7V13ZM7 9H17V7H7V9ZM12.5375 4.0375C12.6792 3.89583 12.75 3.71667 12.75 3.5C12.75 3.28333 12.6792 3.10417 12.5375 2.9625C12.3958 2.82083 12.2167 2.75 12 2.75C11.7833 2.75 11.6042 2.82083 11.4625 2.9625C11.3208 3.10417 11.25 3.28333 11.25 3.5C11.25 3.71667 11.3208 3.89583 11.4625 4.0375C11.6042 4.17917 11.7833 4.25 12 4.25C12.2167 4.25 12.3958 4.17917 12.5375 4.0375ZM14.4625 21.5375C13.4875 20.5625 13 19.3833 13 18C13 16.6167 13.4875 15.4375 14.4625 14.4625C15.4375 13.4875 16.6167 13 18 13C19.3833 13 20.5625 13.4875 21.5375 14.4625C22.5125 15.4375 23 16.6167 23 18C23 19.3833 22.5125 20.5625 21.5375 21.5375C20.5625 22.5125 19.3833 23 18 23C16.6167 23 15.4375 22.5125 14.4625 21.5375ZM18 21.5C18.9 21.5 19.6792 21.2 20.3375 20.6C20.9958 20 21.375 19.2583 21.475 18.375C21.3917 18.4083 21.3125 18.4375 21.2375 18.4625C21.1625 18.4875 21.0833 18.5 21 18.5H20C19.7167 18.5 19.4792 18.4042 19.2875 18.2125C19.0958 18.0208 19 17.7833 19 17.5V17H17V16C17 15.7167 17.0958 15.4792 17.2875 15.2875C17.4792 15.0958 17.7167 15 18 15H18.5C18.5 14.9167 18.5083 14.8375 18.525 14.7625C18.5417 14.6875 18.5667 14.6167 18.6 14.55C18.5 14.5333 18.4 14.5208 18.3 14.5125C18.2 14.5042 18.1 14.5 18 14.5C17.0333 14.5 16.2083 14.8417 15.525 15.525C14.8417 16.2083 14.5 17.0333 14.5 18H16.5C17.05 18 17.5208 18.1958 17.9125 18.5875C18.3042 18.9792 18.5 19.45 18.5 20V20.5H17V21.35C17.1667 21.4 17.3292 21.4375 17.4875 21.4625C17.6458 21.4875 17.8167 21.5 18 21.5Z\" fill=\"currentColor\"/>\n</svg>\n",
        "sprout": "<svg aria-hidden=\"true\" data-tp-original=\"30\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n<path d=\"M11 21V13.025C9.93333 13.025 8.90833 12.8208 7.925 12.4125C6.94167 12.0042 6.075 11.425 5.325 10.675C4.575 9.925 4 9.05833 3.6 8.075C3.2 7.09167 3 6.06667 3 5V3H5C6.05 3 7.06667 3.20417 8.05 3.6125C9.03333 4.02083 9.9 4.6 10.65 5.35C11.1667 5.86667 11.5958 6.43333 11.9375 7.05C12.2792 7.66667 12.5417 8.325 12.725 9.025C12.8083 8.90833 12.9 8.79583 13 8.6875C13.1 8.57917 13.2083 8.46667 13.325 8.35C14.075 7.6 14.9417 7.02083 15.925 6.6125C16.9083 6.20417 17.9333 6 19 6H21V8C21 9.06667 20.7958 10.0917 20.3875 11.075C19.9792 12.0583 19.4 12.925 18.65 13.675C17.9 14.425 17.0375 15 16.0625 15.4C15.0875 15.8 14.0667 16 13 16V21H11ZM11 11C11 10.2 10.8458 9.4375 10.5375 8.7125C10.2292 7.9875 9.79167 7.34167 9.225 6.775C8.65833 6.20833 8.0125 5.77083 7.2875 5.4625C6.5625 5.15417 5.8 5 5 5C5 5.8 5.15 6.56667 5.45 7.3C5.75 8.03333 6.18333 8.68333 6.75 9.25C7.31667 9.81667 7.96667 10.25 8.7 10.55C9.43333 10.85 10.2 11 11 11ZM13 14C13.8 14 14.5625 13.85 15.2875 13.55C16.0125 13.25 16.6583 12.8167 17.225 12.25C17.7917 11.6833 18.2292 11.0333 18.5375 10.3C18.8458 9.56667 19 8.8 19 8C18.2 8 17.4333 8.15417 16.7 8.4625C15.9667 8.77083 15.3167 9.20833 14.75 9.775C14.1833 10.3417 13.75 10.9875 13.45 11.7125C13.15 12.4375 13 13.2 13 14Z\" fill=\"currentColor\"/>\n</svg>\n",
        "notebook-pen": "<svg aria-hidden=\"true\" data-tp-original=\"88\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n<path d=\"M14 9.9V8.2C14.55 7.96667 15.1125 7.79167 15.6875 7.675C16.2625 7.55833 16.8667 7.5 17.5 7.5C17.9333 7.5 18.3583 7.53333 18.775 7.6C19.1917 7.66667 19.6 7.75 20 7.85V9.45C19.6 9.3 19.1958 9.1875 18.7875 9.1125C18.3792 9.0375 17.95 9 17.5 9C16.8667 9 16.2583 9.07917 15.675 9.2375C15.0917 9.39583 14.5333 9.61667 14 9.9ZM14 15.4V13.7C14.55 13.4667 15.1125 13.2917 15.6875 13.175C16.2625 13.0583 16.8667 13 17.5 13C17.9333 13 18.3583 13.0333 18.775 13.1C19.1917 13.1667 19.6 13.25 20 13.35V14.95C19.6 14.8 19.1958 14.6875 18.7875 14.6125C18.3792 14.5375 17.95 14.5 17.5 14.5C16.8667 14.5 16.2583 14.575 15.675 14.725C15.0917 14.875 14.5333 15.1 14 15.4ZM14 12.65V10.95C14.55 10.7167 15.1125 10.5417 15.6875 10.425C16.2625 10.3083 16.8667 10.25 17.5 10.25C17.9333 10.25 18.3583 10.2833 18.775 10.35C19.1917 10.4167 19.6 10.5 20 10.6V12.2C19.6 12.05 19.1958 11.9375 18.7875 11.8625C18.3792 11.7875 17.95 11.75 17.5 11.75C16.8667 11.75 16.2583 11.8292 15.675 11.9875C15.0917 12.1458 14.5333 12.3667 14 12.65ZM6.5 16C7.28333 16 8.04583 16.0875 8.7875 16.2625C9.52917 16.4375 10.2667 16.7 11 17.05V7.2C10.3167 6.8 9.59167 6.5 8.825 6.3C8.05833 6.1 7.28333 6 6.5 6C5.9 6 5.30417 6.05833 4.7125 6.175C4.12083 6.29167 3.55 6.46667 3 6.7V16.6C3.58333 16.4 4.1625 16.25 4.7375 16.15C5.3125 16.05 5.9 16 6.5 16ZM13 17.05C13.7333 16.7 14.4708 16.4375 15.2125 16.2625C15.9542 16.0875 16.7167 16 17.5 16C18.1 16 18.6875 16.05 19.2625 16.15C19.8375 16.25 20.4167 16.4 21 16.6V6.7C20.45 6.46667 19.8792 6.29167 19.2875 6.175C18.6958 6.05833 18.1 6 17.5 6C16.7167 6 15.9417 6.1 15.175 6.3C14.4083 6.5 13.6833 6.8 13 7.2V17.05ZM12 20C11.2 19.3667 10.3333 18.875 9.4 18.525C8.46667 18.175 7.5 18 6.5 18C5.8 18 5.1125 18.0917 4.4375 18.275C3.7625 18.4583 3.11667 18.7167 2.5 19.05C2.15 19.2333 1.8125 19.225 1.4875 19.025C1.1625 18.825 1 18.5333 1 18.15V6.1C1 5.91667 1.04583 5.74167 1.1375 5.575C1.22917 5.40833 1.36667 5.28333 1.55 5.2C2.31667 4.8 3.11667 4.5 3.95 4.3C4.78333 4.1 5.63333 4 6.5 4C7.46667 4 8.4125 4.125 9.3375 4.375C10.2625 4.625 11.15 5 12 5.5C12.85 5 13.7375 4.625 14.6625 4.375C15.5875 4.125 16.5333 4 17.5 4C18.3667 4 19.2167 4.1 20.05 4.3C20.8833 4.5 21.6833 4.8 22.45 5.2C22.6333 5.28333 22.7708 5.40833 22.8625 5.575C22.9542 5.74167 23 5.91667 23 6.1V18.15C23 18.5333 22.8375 18.825 22.5125 19.025C22.1875 19.225 21.85 19.2333 21.5 19.05C20.8833 18.7167 20.2375 18.4583 19.5625 18.275C18.8875 18.0917 18.2 18 17.5 18C16.5 18 15.5333 18.175 14.6 18.525C13.6667 18.875 12.8 19.3667 12 20Z\" fill=\"currentColor\"/>\n</svg>\n",
        "leaf": "<svg aria-hidden=\"true\" data-tp-original=\"18\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n<path d=\"M5.4 19.6001C4.65 18.8501 4.0625 17.9835 3.6375 17.0001C3.2125 16.0168 3 15.0001 3 13.9501C3 12.9001 3.2 11.8626 3.6 10.8376C4 9.81262 4.65 8.85012 5.55 7.95012C6.13333 7.36679 6.85417 6.86679 7.7125 6.45012C8.57083 6.03345 9.5875 5.70429 10.7625 5.46262C11.9375 5.22095 13.2792 5.07512 14.7875 5.02512C16.2958 4.97512 17.9833 5.03345 19.85 5.20012C19.9833 6.96679 20.025 8.59179 19.975 10.0751C19.925 11.5585 19.7875 12.896 19.5625 14.0876C19.3375 15.2793 19.0208 16.321 18.6125 17.2126C18.2042 18.1043 17.7 18.8501 17.1 19.4501C16.2167 20.3335 15.2792 20.9793 14.2875 21.3876C13.2958 21.796 12.2833 22.0001 11.25 22.0001C10.1667 22.0001 9.10833 21.7876 8.075 21.3626C7.04167 20.9376 6.15 20.3501 5.4 19.6001ZM8.2 19.2001C8.68333 19.4835 9.17917 19.6876 9.6875 19.8126C10.1958 19.9376 10.7167 20.0001 11.25 20.0001C12.0167 20.0001 12.775 19.846 13.525 19.5376C14.275 19.2293 14.9917 18.7335 15.675 18.0501C15.975 17.7501 16.2792 17.3293 16.5875 16.7876C16.8958 16.246 17.1625 15.5376 17.3875 14.6626C17.6125 13.7876 17.7833 12.7293 17.9 11.4876C18.0167 10.246 18.0333 8.76679 17.95 7.05012C17.1333 7.01679 16.2125 7.00429 15.1875 7.01262C14.1625 7.02095 13.1417 7.10012 12.125 7.25012C11.1083 7.40012 10.1417 7.64179 9.225 7.97512C8.30833 8.30845 7.55833 8.76679 6.975 9.35012C6.225 10.1001 5.70833 10.8418 5.425 11.5751C5.14167 12.3085 5 13.0168 5 13.7001C5 14.6835 5.1875 15.546 5.5625 16.2876C5.9375 17.0293 6.26667 17.5501 6.55 17.8501C7.25 16.5168 8.175 15.2376 9.325 14.0126C10.475 12.7876 11.8167 11.7835 13.35 11.0001C12.15 12.0501 11.1042 13.2376 10.2125 14.5626C9.32083 15.8876 8.65 17.4335 8.2 19.2001Z\" fill=\"currentColor\"/>\n</svg>\n",
        "book-open": "<svg aria-hidden=\"true\" data-tp-original=\"88\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n<path d=\"M14 9.9V8.2C14.55 7.96667 15.1125 7.79167 15.6875 7.675C16.2625 7.55833 16.8667 7.5 17.5 7.5C17.9333 7.5 18.3583 7.53333 18.775 7.6C19.1917 7.66667 19.6 7.75 20 7.85V9.45C19.6 9.3 19.1958 9.1875 18.7875 9.1125C18.3792 9.0375 17.95 9 17.5 9C16.8667 9 16.2583 9.07917 15.675 9.2375C15.0917 9.39583 14.5333 9.61667 14 9.9ZM14 15.4V13.7C14.55 13.4667 15.1125 13.2917 15.6875 13.175C16.2625 13.0583 16.8667 13 17.5 13C17.9333 13 18.3583 13.0333 18.775 13.1C19.1917 13.1667 19.6 13.25 20 13.35V14.95C19.6 14.8 19.1958 14.6875 18.7875 14.6125C18.3792 14.5375 17.95 14.5 17.5 14.5C16.8667 14.5 16.2583 14.575 15.675 14.725C15.0917 14.875 14.5333 15.1 14 15.4ZM14 12.65V10.95C14.55 10.7167 15.1125 10.5417 15.6875 10.425C16.2625 10.3083 16.8667 10.25 17.5 10.25C17.9333 10.25 18.3583 10.2833 18.775 10.35C19.1917 10.4167 19.6 10.5 20 10.6V12.2C19.6 12.05 19.1958 11.9375 18.7875 11.8625C18.3792 11.7875 17.95 11.75 17.5 11.75C16.8667 11.75 16.2583 11.8292 15.675 11.9875C15.0917 12.1458 14.5333 12.3667 14 12.65ZM6.5 16C7.28333 16 8.04583 16.0875 8.7875 16.2625C9.52917 16.4375 10.2667 16.7 11 17.05V7.2C10.3167 6.8 9.59167 6.5 8.825 6.3C8.05833 6.1 7.28333 6 6.5 6C5.9 6 5.30417 6.05833 4.7125 6.175C4.12083 6.29167 3.55 6.46667 3 6.7V16.6C3.58333 16.4 4.1625 16.25 4.7375 16.15C5.3125 16.05 5.9 16 6.5 16ZM13 17.05C13.7333 16.7 14.4708 16.4375 15.2125 16.2625C15.9542 16.0875 16.7167 16 17.5 16C18.1 16 18.6875 16.05 19.2625 16.15C19.8375 16.25 20.4167 16.4 21 16.6V6.7C20.45 6.46667 19.8792 6.29167 19.2875 6.175C18.6958 6.05833 18.1 6 17.5 6C16.7167 6 15.9417 6.1 15.175 6.3C14.4083 6.5 13.6833 6.8 13 7.2V17.05ZM12 20C11.2 19.3667 10.3333 18.875 9.4 18.525C8.46667 18.175 7.5 18 6.5 18C5.8 18 5.1125 18.0917 4.4375 18.275C3.7625 18.4583 3.11667 18.7167 2.5 19.05C2.15 19.2333 1.8125 19.225 1.4875 19.025C1.1625 18.825 1 18.5333 1 18.15V6.1C1 5.91667 1.04583 5.74167 1.1375 5.575C1.22917 5.40833 1.36667 5.28333 1.55 5.2C2.31667 4.8 3.11667 4.5 3.95 4.3C4.78333 4.1 5.63333 4 6.5 4C7.46667 4 8.4125 4.125 9.3375 4.375C10.2625 4.625 11.15 5 12 5.5C12.85 5 13.7375 4.625 14.6625 4.375C15.5875 4.125 16.5333 4 17.5 4C18.3667 4 19.2167 4.1 20.05 4.3C20.8833 4.5 21.6833 4.8 22.45 5.2C22.6333 5.28333 22.7708 5.40833 22.8625 5.575C22.9542 5.74167 23 5.91667 23 6.1V18.15C23 18.5333 22.8375 18.825 22.5125 19.025C22.1875 19.225 21.85 19.2333 21.5 19.05C20.8833 18.7167 20.2375 18.4583 19.5625 18.275C18.8875 18.0917 18.2 18 17.5 18C16.5 18 15.5333 18.175 14.6 18.525C13.6667 18.875 12.8 19.3667 12 20Z\" fill=\"currentColor\"/>\n</svg>\n",
        "search": "<svg aria-hidden=\"true\" data-tp-original=\"73\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n<path d=\"M12 22C10.6167 22 9.31667 21.7375 8.1 21.2125C6.88333 20.6875 5.825 19.975 4.925 19.075C4.025 18.175 3.3125 17.1167 2.7875 15.9C2.2625 14.6833 2 13.3833 2 12C2 10.6167 2.2625 9.31667 2.7875 8.1C3.3125 6.88333 4.025 5.825 4.925 4.925C5.825 4.025 6.88333 3.3125 8.1 2.7875C9.31667 2.2625 10.6167 2 12 2C14.4333 2 16.5625 2.7625 18.3875 4.2875C20.2125 5.8125 21.35 7.725 21.8 10.025H19.75C19.4333 8.80833 18.8625 7.72083 18.0375 6.7625C17.2125 5.80417 16.2 5.08333 15 4.6V5C15 5.55 14.8042 6.02083 14.4125 6.4125C14.0208 6.80417 13.55 7 13 7H11V9C11 9.28333 10.9042 9.52083 10.7125 9.7125C10.5208 9.90417 10.2833 10 10 10H8V12H10V15H9L4.2 10.2C4.15 10.5 4.10417 10.8 4.0625 11.1C4.02083 11.4 4 11.7 4 12C4 14.1833 4.76667 16.0583 6.3 17.625C7.83333 19.1917 9.73333 19.9833 12 20V22ZM21.1 21.5L17.9 18.3C17.55 18.5 17.175 18.6667 16.775 18.8C16.375 18.9333 15.95 19 15.5 19C14.25 19 13.1875 18.5625 12.3125 17.6875C11.4375 16.8125 11 15.75 11 14.5C11 13.25 11.4375 12.1875 12.3125 11.3125C13.1875 10.4375 14.25 10 15.5 10C16.75 10 17.8125 10.4375 18.6875 11.3125C19.5625 12.1875 20 13.25 20 14.5C20 14.95 19.9333 15.375 19.8 15.775C19.6667 16.175 19.5 16.55 19.3 16.9L22.5 20.1L21.1 21.5ZM17.275 16.275C17.7583 15.7917 18 15.2 18 14.5C18 13.8 17.7583 13.2083 17.275 12.725C16.7917 12.2417 16.2 12 15.5 12C14.8 12 14.2083 12.2417 13.725 12.725C13.2417 13.2083 13 13.8 13 14.5C13 15.2 13.2417 15.7917 13.725 16.275C14.2083 16.7583 14.8 17 15.5 17C16.2 17 16.7917 16.7583 17.275 16.275Z\" fill=\"currentColor\"/>\n</svg>\n"
    };

    function icons() {
        r.querySelectorAll("[data-lucide]").forEach(el => {
            const svg = originalIcons[el.getAttribute("data-lucide")];
            if (svg) el.outerHTML = svg
        });
        if (globalThis.lucide) lucide.createIcons({
            attrs: {
                width: 18,
                height: 18
            }
        })
    }

    function say(t) {
        q('#gh-feedback').textContent = t
    }

    function jump(id) {
        q('#' + id).scrollIntoView({
            behavior: matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth',
            block: 'center'
        })
    }

    function dateStr(d) {
        return d.toISOString().slice(0, 10)
    }
    const plantName = id => plants.find(p => p.id === id)?.name || id;

    function taskHTML(t) {
        return '<div class="gh-taskrow ' + (t.done ? 'done' : '') + '"><button class="gh-check" data-complete="' + t.id + '" aria-label="' + esc((t.done ? 'Reopen ' : 'Complete ') + t.title) + '" aria-pressed="' + t.done + '"><img src="' + (t.done ? assets.checked : assets.unchecked) + '" alt=""></button><div class="gh-taskcopy"><h3>' + esc(t.title) + '</h3><p>' + esc(plantName(t.plant)) + ' · ' + t.time + '</p></div><button class="gh-icon" data-action="task" data-id="' + t.id + '" aria-label="Edit or reschedule ' + esc(t.title) + '">' + icon('calendar-clock') + '</button></div>'
    }

    function renderCare() {
        const due = tasks.filter(t => t.date === '2026-10-21' && !t.done);
        q('#gh-todaycount').textContent = due.length + ' to do';
        q('#gh-nearest-list').innerHTML = due.length ? due.slice(0, 2).map(taskHTML).join('') : '<div class="gh-empty">All caught up for today.</div>';
        const start = new Date('2026-10-19T12:00:00Z');
        start.setUTCDate(start.getUTCDate() + weekOffset * 7);
        q('#gh-month').textContent = start.toLocaleDateString('en', {
            month: 'long',
            year: 'numeric',
            timeZone: 'UTC'
        });
        q('#gh-week').innerHTML = Array.from({
            length: 7
        }, (_, i) => {
            const d = new Date(start);
            d.setUTCDate(d.getUTCDate() + i);
            const s = dateStr(d),
                count = tasks.filter(t => t.date === s && !t.done).length;
            return '<button class="gh-day" data-date="' + s + '" aria-pressed="' + (s === selectedDate) + '" aria-label="' + d.toLocaleDateString('en', {
                month: 'long',
                day: 'numeric',
                timeZone: 'UTC'
            }) + ', ' + count + ' pending tasks"><span>' + d.toLocaleDateString('en', {
                weekday: 'short',
                timeZone: 'UTC'
            }) + '</span><strong>' + d.getUTCDate() + '</strong><i style="visibility:' + (count ? 'visible' : 'hidden') + '"></i></button>'
        }).join('');
        const list = tasks.filter(t => t.date === selectedDate && t.done === (filter === 'done')).sort((a, b) => a.time.localeCompare(b.time));
        q('#gh-task-list').innerHTML = list.length ? list.map(taskHTML).join('') : '<div class="gh-empty">' + (filter === 'done' ? 'No completed tasks on this date.' : 'Nothing scheduled. A little room to grow.') + '</div>';
        icons()
    }

    function renderPlants() {
        q('#gh-plantcount').textContent = plants.filter(p => p.status === 'Active').length + ' active';
        q('#gh-carousel').innerHTML = plants.map(p => '<article class="gh-plantcard" aria-label="' + esc(p.name) + '"><div class="gh-plantvisual ' + (p.id === 'tomato' ? 'tomato' : '') + '"><div><div class="gh-overline">MY GARDEN</div><div style="font:600 30px Lora,Georgia,serif;color:#285b43">My Balcony</div></div><img src="' + p.image + '" alt="' + esc(p.name) + ' reference photo"></div><div class="gh-plantbody"><div class="gh-row gh-between"><h3>' + esc(p.name) + '</h3><span class="gh-pill">' + esc(p.status) + '</span></div><div class="gh-plantmeta"><span>' + esc(p.pot) + ' · My Balcony</span><span>Since ' + new Date(p.start + 'T12:00:00Z').toLocaleDateString('en', {
            day: 'numeric',
            month: 'short',
            timeZone: 'UTC'
        }) + '</span></div><div class="gh-plantactions"><button class="gh-link" data-action="plant" data-id="' + p.id + '">View plant ' + icon('arrow-up-right') + '</button><button class="gh-icon" data-action="task" data-plant="' + p.id + '" aria-label="Add care task for ' + esc(p.name) + '">' + icon('droplets') + '</button><button class="gh-icon" data-action="journal" data-plant="' + p.id + '" aria-label="Add journal entry for ' + esc(p.name) + '">' + icon('notebook-pen') + '</button></div></div></article>').join('');
        const p = plants.find(p => p.id === 'tomato');
        if (p) {
            q('#gh-growthtitle').textContent = p.name + ' · ' + p.stage;
            q('#gh-growing').style.setProperty('--gh-stem', (8 + stages.indexOf(p.stage) * 7) + 'px')
        }
        updateSlide();
        icons()
    }

    function renderPlan() {
        q('#gh-planitems').innerHTML = plans.map(p => '<div class="gh-planrow">' + icon('sprout') + '<div><h3>' + esc(p.name) + '</h3><p>' + esc(p.pot) + ' · Balcony Plan</p></div><button class="gh-btn ' + (p.planted ? 'secondary' : '') + '" data-planted="' + p.id + '" ' + (p.planted ? 'disabled' : '') + '>' + (p.planted ? 'In My Plants' : 'Mark as planted') + '</button></div>').join('');
        icons()
    }

    function renderJournal() {
        q('#gh-journal-list').innerHTML = entries.slice().sort((a, b) => b.date.localeCompare(a.date)).slice(0, 2).map(e => '<div class="gh-journalrow"><div class="gh-journaldate">' + Number(e.date.slice(-2)) + '<small>' + new Date(e.date + 'T12:00:00Z').toLocaleDateString('en', {
            month: 'short',
            timeZone: 'UTC'
        }).toUpperCase() + '</small></div><div><h3>' + esc(e.note) + '</h3><p>' + esc(plantName(e.plant)) + ' · ' + esc(e.type) + (e.quantity ? ' · ' + esc(e.quantity) + ' ' + esc(e.unit) : '') + '</p></div><button class="gh-icon" data-action="journal" data-id="' + e.id + '" aria-label="Edit journal entry">' + icon('arrow-up-right') + '</button></div>').join('');
        icons()
    }

    function stopAuto() {
        auto = false;
        clearInterval(timer);
        q('#gh-autoplay').setAttribute('aria-pressed', 'false');
        q('#gh-autoplay').innerHTML = icon('play') + '<span>Auto slide</span>';
        icons()
    }

    function slide(dir) {
        const c = q('#gh-carousel'),
            card = c.querySelector('.gh-plantcard');
        if (!card) return;
        const max = c.scrollWidth - c.clientWidth;
        const next = c.scrollLeft + dir * (card.offsetWidth + 16);
        c.scrollTo({
            left: next > max + 3 ? 0 : next < 0 ? max : next,
            behavior: matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth'
        })
    }

    function updateSlide() {
        const c = q('#gh-carousel'),
            card = c.querySelector('.gh-plantcard');
        q('#gh-slidecount').textContent = (card ? Math.min(plants.length, Math.round(c.scrollLeft / (card.offsetWidth + 16)) + 1) : 0) + ' / ' + plants.length
    }
    r.addEventListener('click', e => {
        const b = e.target.closest('button');
        if (!b) return;
        if (b.dataset.jump) {
            jump(b.dataset.jump);
            qa('.gh-navlinks button').forEach(x => x.classList.toggle('active', x === b))
        }
        if (b.dataset.complete) {
            const t = tasks.find(x => x.id == b.dataset.complete);
            t.done = !t.done;
            renderCare();
            say(t.title + (t.done ? ' completed.' : ' reopened.'))
        }
        if (b.dataset.date) {
            selectedDate = b.dataset.date;
            renderCare()
        }
        if (b.dataset.filter) {
            filter = b.dataset.filter;
            qa('[data-filter]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
            renderCare()
        }
        if (b.dataset.planted) {
            const p = plans.find(x => x.id === b.dataset.planted);
            if (p.planted) return;
            p.planted = true;
            plants.push({
                id: p.id,
                name: p.name,
                pot: p.pot,
                stage: 'Planted',
                status: 'Active',
                start: '2026-10-21',
                source: 'Balcony Plan',
                image: assets.sprout
            });
            renderPlan();
            renderPlants();
            say(p.name + ' added to My Plants from Balcony Plan.');
            jump('gh-plants')
        }
    });
    q('#gh-prev').onclick = () => {
        stopAuto();
        slide(-1)
    };
    q('#gh-next').onclick = () => {
        stopAuto();
        slide(1)
    };
    q('#gh-carousel').addEventListener('scroll', updateSlide, {
        passive: true
    });
    q('#gh-carousel').addEventListener('pointerdown', stopAuto);
    let drag = null;
    const rail = q('#gh-carousel');
    rail.addEventListener('pointerdown', e => {
        if (e.pointerType !== 'mouse' || e.target.closest('button')) return;
        drag = {
            x: e.clientX,
            left: rail.scrollLeft,
            id: e.pointerId,
            moved: false
        }
    });
    rail.addEventListener('pointermove', e => {
        if (!drag) return;
        const delta = e.clientX - drag.x;
        if (Math.abs(delta) > 6) {
            drag.moved = true;
            rail.setPointerCapture(e.pointerId);
            rail.style.scrollSnapType = 'none';
            rail.scrollLeft = drag.left - delta
        }
    });

    function endDrag() {
        if (!drag) return;
        rail.style.scrollSnapType = '';
        drag = null
    }
    rail.addEventListener('pointerup', endDrag);
    rail.addEventListener('pointercancel', endDrag);
    q('#gh-carousel').addEventListener('focusin', stopAuto);
    q('#gh-carousel').addEventListener('mouseenter', () => {
        if (auto) stopAuto()
    });
    q('#gh-autoplay').onclick = () => {
        if (auto) {
            stopAuto();
            return
        }
        auto = true;
        q('#gh-autoplay').setAttribute('aria-pressed', 'true');
        q('#gh-autoplay').innerHTML = icon('pause') + '<span>Pause slide</span>';
        icons();
        timer = setInterval(() => {
            if (!document.hidden && r.isConnected) slide(1);
            else stopAuto()
        }, 6500)
    };
    q('#gh-weekprev').onclick = () => {
        weekOffset--;
        const d = new Date('2026-10-19T12:00:00Z');
        d.setUTCDate(d.getUTCDate() + weekOffset * 7);
        selectedDate = dateStr(d);
        renderCare()
    };
    q('#gh-weeknext').onclick = () => {
        weekOffset++;
        const d = new Date('2026-10-19T12:00:00Z');
        d.setUTCDate(d.getUTCDate() + weekOffset * 7);
        selectedDate = dateStr(d);
        renderCare()
    };
    renderCare();
    renderPlants();
    renderPlan();
    renderJournal();
    if (globalThis.Tweak) {
        const settings = {
            weatherGradient: true
        };
        const tw = new Tweak({
            container: r,
            onChange: () => q('.gh-weather').style.background = settings.weatherGradient ? 'linear-gradient(135deg,#c4dfee,#e3ebd5 60%,#f9edbc)' : '#e3ebd5'
        });
        tw.addToggle(settings, 'weatherGradient', {
            label: 'Weather gradient'
        })
    }
})();

(() => {
    const root = document.getElementById('tp-garden-home');

    function page(which) {
        root.querySelector('#tp-public-view').hidden = which !== 'public';
        root.querySelector('#tp-home-view').hidden = which !== 'home';
        root.querySelectorAll('[data-page]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.page === which)));
        root.scrollIntoView({
            behavior: 'auto',
            block: 'start'
        });
        if (which === 'public') {
            const btn = root.querySelector('#gh-autoplay');
            if (btn.getAttribute('aria-pressed') === 'true') btn.click()
        }
    }
    root.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => page(b.dataset.page)));
    root.querySelectorAll('[data-demo-home]').forEach(b => b.addEventListener('click', () => page('home')));
    root.querySelectorAll('[data-public-jump]').forEach(b => b.addEventListener('click', () => root.querySelector('#' + b.dataset.publicJump).scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    })));
    root.querySelector('#gp-signup').addEventListener('click', () => {
        root.querySelector('#gp-signup-message').textContent = 'Preview: this opens sign up, then Garden Setup. Try the sample garden above.'
    });
})();

// Route only the Plant Care module; other modules remain visual examples.
const cfg = JSON.parse(document.getElementById('landing-config').textContent);
const landingRoot = document.getElementById('tp-garden-home');
landingRoot.addEventListener('click', event => {
    const b = event.target.closest('button');
    if (!b) return;
    if (b.dataset.jump === 'gh-schedule' || b.dataset.action === 'task') {
        event.preventDefault();
        event.stopImmediatePropagation();
        const plant = b.dataset.plant || (b.dataset.id === '2' ? 'tomato' : 'mint');
        const url = b.dataset.jump === 'gh-schedule' ? cfg.careUrl : (cfg.plantUrls[plant] || cfg.careUrl);
        location.assign(url + (b.dataset.action === 'task' && !b.dataset.id ? '?action=add' : ''));
    }
}, true);
landingRoot.querySelector('[data-page="' + cfg.initialView + '"]').click();
if (['#gh-space', '#gh-plan', '#gh-plants', '#gh-journal'].includes(location.hash)) {
    landingRoot.querySelector('[data-page="home"]').click();
    landingRoot.querySelector(location.hash)?.scrollIntoView({
        block: 'center'
    });
}
