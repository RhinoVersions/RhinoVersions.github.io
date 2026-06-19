const test = require('node:test');
const assert = require('node:assert');
const {
    parseMarkdownLinks,
    parseVersionFromFilename,
    compareFullVersions,
    formatDate,
    getRelativeTime,
    resolveTheme,
    getVersionBuildKey
} = require('../assets/js/script.js');

// Mock window for resolveTheme
global.window = {
    matchMedia: (query) => ({
        matches: query.includes('dark'), // Mocking prefers-color-scheme: dark
    })
};

test('parseMarkdownLinks', async (t) => {
    await t.test('should parse valid links', () => {
        const markdown = '- [rhino_en-us_8.24.25281.15001.exe](https://example.com/win.exe)\n- [rhino_8.25.25328.11002.dmg](https://example.com/mac.dmg)';
        const links = parseMarkdownLinks(markdown);
        assert.strictEqual(links.length, 2);
        assert.strictEqual(links[0].filename, 'rhino_en-us_8.24.25281.15001.exe');
        assert.strictEqual(links[0].url, 'https://example.com/win.exe');
        assert.strictEqual(links[1].filename, 'rhino_8.25.25328.11002.dmg');
        assert.strictEqual(links[1].url, 'https://example.com/mac.dmg');
    });

    await t.test('should return empty array for invalid markdown', () => {
        const markdown = 'No links here';
        const links = parseMarkdownLinks(markdown);
        assert.strictEqual(links.length, 0);
    });
});

test('parseVersionFromFilename', async (t) => {
    await t.test('should parse Windows filename', () => {
        const filename = 'rhino_en-us_8.24.25281.15001.exe';
        const info = parseVersionFromFilename(filename);
        assert.strictEqual(info.major, '8');
        assert.strictEqual(info.minor, '24');
        assert.strictEqual(info.locale, 'en-us');
        assert.strictEqual(info.platform, 'windows');
        assert.strictEqual(info.fullVersion, '8.24.25281.15001');
        // 25281 -> 2025 day 281 -> 2025-10-08
        assert.strictEqual(info.dateString, '2025-10-08');
    });

    await t.test('should parse Windows WIP filename (no locale, multilingual)', () => {
        const filename = 'rhino_9.0.26132.12305.exe';
        const info = parseVersionFromFilename(filename);
        assert.strictEqual(info.major, '9');
        assert.strictEqual(info.minor, '0');
        assert.strictEqual(info.locale, 'multi');
        assert.strictEqual(info.platform, 'windows');
        assert.strictEqual(info.fullVersion, '9.0.26132.12305');
    });

    await t.test('should parse Mac filename (no locale)', () => {
        const filename = 'rhino_8.25.25328.11002.dmg';
        const info = parseVersionFromFilename(filename);
        assert.strictEqual(info.major, '8');
        assert.strictEqual(info.minor, '25');
        assert.strictEqual(info.locale, 'multi');
        assert.strictEqual(info.platform, 'mac');
        // 25328 -> 2025 day 328 -> 2025-11-24
        assert.strictEqual(info.dateString, '2025-11-24');
    });

    await t.test('should return null for invalid filename', () => {
        const filename = 'invalid_file.txt';
        const info = parseVersionFromFilename(filename);
        assert.strictEqual(info, null);
    });
});

test('compareFullVersions', async (t) => {
    await t.test('should correctly compare versions', () => {
        assert.ok(compareFullVersions('8.25.25328.11002', '8.24.25281.15001') > 0);
        assert.ok(compareFullVersions('8.24.25281.15001', '8.25.25328.11002') < 0);
        assert.strictEqual(compareFullVersions('8.24.25281.15001', '8.24.25281.15001'), 0);
        assert.ok(compareFullVersions('8.24.25281.15002', '8.24.25281.15001') > 0);
    });
});

test('formatDate', async (t) => {
    await t.test('should format date correctly', () => {
        const date = new Date(2025, 9, 8); // Oct 8, 2025
        const formatted = formatDate(date, 'long');
        // Using includes to be resilient to different space characters or tiny Intl variations
        assert.ok(formatted.includes('October'));
        assert.ok(formatted.includes('8'));
        assert.ok(formatted.includes('2025'));
    });
});

test('getRelativeTime', async (t) => {
    await t.test('should format relative time correctly', () => {
        const now = new Date();
        const today = new Date(now);
        const yesterday = new Date(now.getTime() - 1 * 24 * 60 * 60 * 1000);
        const threeDaysAgo = new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000);
        const lastMonth = new Date(now.getTime() - 35 * 24 * 60 * 60 * 1000);
        const twoYearsAgo = new Date(now.getTime() - 2 * 365 * 24 * 60 * 60 * 1000);

        assert.strictEqual(getRelativeTime(today), 'today');
        assert.strictEqual(getRelativeTime(yesterday), 'yesterday');
        assert.strictEqual(getRelativeTime(threeDaysAgo), '3 days ago');
        assert.strictEqual(getRelativeTime(lastMonth), 'last month');
        assert.strictEqual(getRelativeTime(twoYearsAgo), '2 years ago');
    });
});

test('resolveTheme', async (t) => {
    await t.test('should resolve explicit themes', () => {
        assert.strictEqual(resolveTheme('light'), 'light');
        assert.strictEqual(resolveTheme('dark'), 'dark');
    });

    await t.test('should resolve system theme', () => {
        // Our mock matchMedia returns matches: true for 'dark'
        assert.strictEqual(resolveTheme('system'), 'dark');
    });
});

test('getVersionBuildKey', async (t) => {
    await t.test('should return major.minor', () => {
        assert.strictEqual(getVersionBuildKey('8.24.25281.15001'), '8.24.25281');
        assert.strictEqual(getVersionBuildKey('7.31.25281.15001'), '7.31.25281');
        // Windows exe and its Mac dmg (+1 last digit, same day) share a build key
        assert.strictEqual(getVersionBuildKey('8.24.25281.15002'), '8.24.25281');
        // Distinct Rhino 9 WIP builds (all 9.0) stay separate by day
        assert.notStrictEqual(getVersionBuildKey('9.0.26167.11545'), getVersionBuildKey('9.0.26160.12305'));
    });
});
