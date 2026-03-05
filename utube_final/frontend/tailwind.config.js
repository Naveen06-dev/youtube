
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                yt: {
                    red: '#FF0000',
                    black: '#0f0f0f',
                    grey: '#272727',
                    light: '#f1f1f1'
                }
            },
            animation: {
                'glow': 'glow 2s ease-in-out infinite alternate',
                'float': 'float 6s ease-in-out infinite',
            },
            keyframes: {
                glow: {
                    '0%': { boxShadow: '0 0 5px rgba(255, 0, 0, 0.2)' },
                    '100%': { boxShadow: '0 0 20px rgba(255, 0, 0, 0.6)' },
                },
                float: {
                    '0%, 100%': { transform: 'translateY(0)' },
                    '50%': { transform: 'translateY(-20px)' },
                }
            }
        },
    },
    plugins: [],
}
