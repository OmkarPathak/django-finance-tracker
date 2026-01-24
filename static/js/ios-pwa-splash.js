/**
 * iOS PWA Splash Screen Generator
 * Dynamically creates a sized splash screen image for iOS devices
 * avoiding the need for 20+ static image files.
 */
(function() {
    // Only run on iOS (including iPadOS which masquerades as Mac)
    const isIos = /iphone|ipad|ipod/.test(window.navigator.userAgent.toLowerCase()) || 
                  (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    if (!isIos) {
        return;
    }

    // Configuration
    const iconUrl = '/static/img/pwa-icon-512.png';
    const backgroundColor = '#023047'; // Brand Dark Blue

    function createSplashScreen() {
        const width = window.screen.width * window.devicePixelRatio;
        const height = window.screen.height * window.devicePixelRatio;

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');

        // Draw Background
        ctx.fillStyle = backgroundColor;
        ctx.fillRect(0, 0, width, height);

        // Load Icon
        const img = new Image();
        // img.crossOrigin = 'Anonymous'; // Removed: Causes issues with local static files if headers are missing
        img.src = iconUrl;
        
        img.onerror = function() {
            console.error('Failed to load PWA icon for splash screen generation.');
        };
        
        img.onload = function() {
            // Draw Icon Centered
            // Use 1/4th of the screen width or 512px, whichever is smaller
            const iconSize = Math.min(width * 0.4, 512); 
            const x = (width - iconSize) / 2;
            const y = (height - iconSize) / 2;
            const cornerRadius = iconSize * 0.2; // approx standard iOS curve

            ctx.save();
            ctx.beginPath();
            // Draw rounded rectangle path for clipping
            ctx.moveTo(x + cornerRadius, y);
            ctx.lineTo(x + iconSize - cornerRadius, y);
            ctx.quadraticCurveTo(x + iconSize, y, x + iconSize, y + cornerRadius);
            ctx.lineTo(x + iconSize, y + iconSize - cornerRadius);
            ctx.quadraticCurveTo(x + iconSize, y + iconSize, x + iconSize - cornerRadius, y + iconSize);
            ctx.lineTo(x + cornerRadius, y + iconSize);
            ctx.quadraticCurveTo(x, y + iconSize, x, y + iconSize - cornerRadius);
            ctx.lineTo(x, y + cornerRadius);
            ctx.quadraticCurveTo(x, y, x + cornerRadius, y);
            ctx.closePath();
            ctx.clip();

            ctx.drawImage(img, x, y, iconSize, iconSize);
            ctx.restore();

            // Create Link Tag
            const dataUrl = canvas.toDataURL('image/png');
            
            // Remove existing tag if any
            const existing = document.querySelector('link[rel="apple-touch-startup-image"]');
            if (existing) {
                existing.href = dataUrl;
            } else {
                const link = document.createElement('link');
                link.setAttribute('rel', 'apple-touch-startup-image');
                link.setAttribute('href', dataUrl);
                document.head.appendChild(link);
            }
            console.log('iOS Splash Screen generated successfully.');
        };
    }

    // Run on load
    if (document.readyState === 'complete') {
        createSplashScreen();
    } else {
        window.addEventListener('load', createSplashScreen);
    }
})();
