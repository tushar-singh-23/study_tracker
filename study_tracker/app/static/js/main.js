document.addEventListener('DOMContentLoaded', function() {
    const circles = document.querySelectorAll('.circular-chart .circle');
    circles.forEach(circle => {
        const percentage = circle.getAttribute('stroke-dasharray').split(',')[0];
        circle.style.setProperty('--percent', percentage);
    });
});
