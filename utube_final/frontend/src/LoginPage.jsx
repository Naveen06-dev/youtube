
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import {
    Mail, Lock, User, Eye, EyeOff, Github,
    Chrome, CheckCircle2, AlertCircle, Play,
    Zap, Sparkles, TrendingUp, Search
} from 'lucide-react';
import './LoginPage.css';

const LoginPage = ({ onLogin }) => {
    const [isLogin, setIsLogin] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    // Parallax mouse effect
    const mouseX = useMotionValue(0);
    const mouseY = useMotionValue(0);

    const handleMouseMove = (e) => {
        const { clientX, clientY } = e;
        const { innerWidth, innerHeight } = window;
        mouseX.set(clientX / innerWidth);
        mouseY.set(clientY / innerHeight);
    };

    const rotateX = useTransform(mouseY, [0, 1], [5, -5]);
    const rotateY = useTransform(mouseX, [0, 1], [-5, 5]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');

        // Simulate Auth
        setTimeout(() => {
            if (isLogin) {
                // Mock validation
                const formData = new FormData(e.target);
                const email = formData.get('email');
                if (email === 'error@test.com') {
                    setError('Invalid credentials. Please try again.');
                    setIsLoading(false);
                } else {
                    setSuccess(true);
                    setTimeout(() => {
                        onLogin({
                            id: 'user_' + Math.random().toString(36).substr(2, 9),
                            name: email.split('@')[0],
                            email: email,
                            avatar: `https://ui-avatars.com/api/?name=${email}&background=FF0000&color=fff`
                        });
                    }, 1500);
                }
            } else {
                // Sign up simulation
                setSuccess(true);
                setTimeout(() => setIsLogin(true), 1500);
            }
        }, 2000);
    };

    return (
        <div
            className="min-h-screen w-full bg-[#0f0f0f] flex items-center justify-center p-4 md:p-8 relative overflow-hidden"
            onMouseMove={handleMouseMove}
        >
            {/* Dynamic Background Elements */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <motion.div
                    animate={{
                        scale: [1, 1.2, 1],
                        x: [0, 50, 0],
                        y: [0, 30, 0],
                    }}
                    transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                    className="absolute -top-[10%] -left-[10%] w-[50%] h-[50%] bg-red-600/10 rounded-full blur-[120px]"
                />
                <motion.div
                    animate={{
                        scale: [1, 1.3, 1],
                        x: [0, -40, 0],
                        y: [0, -60, 0],
                    }}
                    transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
                    className="absolute -bottom-[10%] -right-[10%] w-[60%] h-[60%] bg-blue-600/5 rounded-full blur-[100px]"
                />

                {/* Floating Particles/Blobs */}
                {[...Array(15)].map((_, i) => (
                    <motion.div
                        key={i}
                        className="absolute w-1 h-1 bg-white/20 rounded-full"
                        initial={{
                            x: Math.random() * window.innerWidth,
                            y: Math.random() * window.innerHeight
                        }}
                        animate={{
                            y: [0, -100, 0],
                            opacity: [0.2, 0.5, 0.2],
                        }}
                        transition={{
                            duration: 5 + Math.random() * 10,
                            repeat: Infinity,
                            delay: Math.random() * 10,
                        }}
                    />
                ))}
            </div>

            <div className="w-full max-w-6xl flex flex-col md:flex-row gap-8 items-center z-10">

                {/* Left Side: Animated Illustration / AI Visualization */}
                <div className="hidden md:flex flex-1 flex-col items-start gap-8">
                    <motion.div
                        initial={{ opacity: 0, x: -50 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.8 }}
                    >
                        <div className="flex items-center gap-3 mb-4">
                            <div className="p-3 bg-yt-red rounded-2xl shadow-[0_0_20px_rgba(255,0,0,0.5)]">
                                <Sparkles className="text-white w-6 h-6" />
                            </div>
                            <h2 className="text-4xl font-bold tracking-tight">AI Powered <br />Recommendations</h2>
                        </div>
                        <p className="text-white/60 text-lg max-w-md">
                            Experience the next generation of video discovery. Our neural network
                            learns your tastes in real-time to curate the perfect feed.
                        </p>
                    </motion.div>

                    <div className="relative w-full h-[400px]">
                        {/* Recommendation Visualizer */}
                        <motion.div
                            className="absolute inset-0 flex items-center justify-center"
                            animate={{ rotate: 360 }}
                            transition={{ duration: 50, repeat: Infinity, ease: "linear" }}
                        >
                            <div className="w-[300px] h-[300px] border border-white/5 rounded-full relative">
                                {[...Array(6)].map((_, i) => (
                                    <motion.div
                                        key={i}
                                        className="absolute w-12 h-12 bg-yt-grey border border-white/10 rounded-xl flex items-center justify-center"
                                        style={{
                                            top: '50%',
                                            left: '50%',
                                            transform: `rotate(${i * 60}deg) translate(150px) rotate(-${i * 60}deg)`
                                        }}
                                        animate={{ scale: [1, 1.1, 1] }}
                                        transition={{ duration: 2, repeat: Infinity, delay: i * 0.3 }}
                                    >
                                        <Play className="w-5 h-5 text-yt-red fill-yt-red" />
                                    </motion.div>
                                ))}
                            </div>
                        </motion.div>

                        {/* Neural Hub Center */}
                        <div className="absolute inset-0 flex items-center justify-center">
                            <motion.div
                                className="w-24 h-24 bg-yt-red/20 rounded-full flex items-center justify-center relative"
                                animate={{ scale: [1, 1.15, 1] }}
                                transition={{ duration: 3, repeat: Infinity }}
                            >
                                <div className="absolute inset-0 bg-yt-red rounded-full blur-2xl opacity-40 animate-pulse" />
                                <Zap className="w-10 h-10 text-yt-red fill-yt-red relative z-10" />
                            </motion.div>

                            {/* Pulsating rings */}
                            <motion.div
                                className="absolute w-32 h-32 border-2 border-yt-red/30 rounded-full"
                                animate={{ scale: [1, 1.5], opacity: [1, 0] }}
                                transition={{ duration: 2, repeat: Infinity }}
                            />
                            <motion.div
                                className="absolute w-32 h-32 border-2 border-yt-red/20 rounded-full"
                                animate={{ scale: [1, 1.8], opacity: [1, 0] }}
                                transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
                            />
                        </div>

                        {/* Floating Info Cards */}
                        <motion.div
                            animate={{ y: [0, -10, 0] }}
                            transition={{ duration: 10, repeat: Infinity }}
                            className="absolute top-10 right-0 glass-card p-4 rounded-2xl flex items-center gap-3"
                        >
                            <TrendingUp className="text-green-500 w-5 h-5" />
                            <div className="text-sm">
                                <p className="font-semibold">Trend Analysis</p>
                                <p className="text-white/40">Real-time sync...</p>
                            </div>
                        </motion.div>

                        <motion.div
                            animate={{ y: [0, 10, 0] }}
                            transition={{ duration: 8, repeat: Infinity, delay: 1 }}
                            className="absolute bottom-10 left-0 glass-card p-4 rounded-2xl flex items-center gap-3"
                        >
                            <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                                <Search className="text-blue-500 w-4 h-4" />
                            </div>
                            <div className="text-sm">
                                <p className="font-semibold">Deep Search</p>
                                <p className="text-white/40">Indexing 50k+ nodes</p>
                            </div>
                        </motion.div>
                    </div>
                </div>

                {/* Right Side: Auth Form */}
                <motion.div
                    style={{ rotateX, rotateY }}
                    className="w-full max-w-md perspective-1000"
                >
                    <motion.div
                        className="glass-card p-8 md:p-10 rounded-[2.5rem] shadow-2xl relative overflow-hidden"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.5 }}
                    >
                        {/* Header */}
                        <div className="text-center mb-10">
                            <motion.div
                                className="inline-flex p-4 rounded-2xl bg-yt-red mb-6"
                                whileHover={{ rotate: 10, scale: 1.1 }}
                            >
                                <Play className="w-10 h-10 text-white fill-white" />
                            </motion.div>
                            <h1 className="text-3xl font-bold mb-2 tracking-tight">
                                {isLogin ? 'Welcome Back' : 'Join N-Tube'}
                            </h1>
                            <p className="text-white/40">
                                {isLogin ? 'Sign in to continue your journey' : 'Create an account to get started'}
                            </p>
                        </div>

                        {/* Error/Success Feedbacks */}
                        <AnimatePresence>
                            {error && (
                                <motion.div
                                    initial={{ opacity: 0, y: -10 }}
                                    animate={{ opacity: 1, y: 0, x: [0, -5, 5, -5, 5, 0] }}
                                    exit={{ opacity: 0, y: -10 }}
                                    className="bg-red-500/10 border border-red-500/20 text-red-500 p-4 rounded-xl mb-6 flex items-center gap-3"
                                >
                                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                                    <p className="text-sm font-medium">{error}</p>
                                </motion.div>
                            )}
                            {success && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="absolute inset-0 z-50 bg-[#0f0f0ff2] backdrop-blur-md flex flex-col items-center justify-center"
                                >
                                    <motion.div
                                        animate={{ scale: [0, 1.2, 1] }}
                                        transition={{ type: "spring" }}
                                        className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center shadow-[0_0_30px_rgba(34,197,94,0.4)]"
                                    >
                                        <CheckCircle2 className="w-10 h-10 text-white" />
                                    </motion.div>
                                    <p className="text-2xl font-bold mt-6">Redirecting...</p>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="space-y-5">
                            {!isLogin && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    className="space-y-2"
                                >
                                    <label className="text-sm font-medium text-white/60 ml-1">Full Name</label>
                                    <div className="relative group">
                                        <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30 group-focus-within:text-yt-red transition-colors" />
                                        <input
                                            type="text"
                                            name="fullname"
                                            className="input-field w-full pl-12"
                                            placeholder="John Doe"
                                            required={!isLogin}
                                        />
                                    </div>
                                </motion.div>
                            )}

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-white/60 ml-1">Email Address</label>
                                <div className="relative group">
                                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30 group-focus-within:text-yt-red transition-colors" />
                                    <input
                                        type="email"
                                        name="email"
                                        className="input-field w-full pl-12"
                                        placeholder="name@example.com"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <div className="flex justify-between items-center px-1">
                                    <label className="text-sm font-medium text-white/60">Password</label>
                                    {isLogin && <button type="button" className="text-sm text-yt-red hover:text-red-400 transition-colors">Forgot?</button>}
                                </div>
                                <div className="relative group">
                                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30 group-focus-within:text-yt-red transition-colors" />
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        name="password"
                                        className="input-field w-full pl-12 pr-12"
                                        placeholder="••••••••"
                                        required
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-4 top-1/2 -translate-y-1/2 text-white/30 hover:text-white"
                                    >
                                        {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                    </button>
                                </div>

                                {!isLogin && (
                                    <div className="px-1 pt-2">
                                        <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                            <motion.div
                                                className="h-full bg-yt-red"
                                                initial={{ width: 0 }}
                                                animate={{ width: '40%' }}
                                            />
                                        </div>
                                        <p className="text-[10px] text-white/30 mt-1 uppercase tracking-wider">Password strength: Medium</p>
                                    </div>
                                )}
                            </div>

                            {isLogin && (
                                <div className="flex items-center gap-2 px-1">
                                    <input type="checkbox" className="w-4 h-4 rounded border-white/10 bg-white/5 accent-yt-red" />
                                    <span className="text-sm text-white/40">Remember me</span>
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={isLoading}
                                className="btn-primary w-full mt-4 flex items-center justify-center gap-2"
                            >
                                {isLoading ? (
                                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                ) : (
                                    <>
                                        <span>{isLogin ? 'Login' : 'Create Account'}</span>
                                        <Sparkles className="w-4 h-4" />
                                    </>
                                )}
                            </button>
                        </form>

                        <div className="mt-8">
                            <div className="relative flex items-center justify-center mb-6">
                                <div className="w-full h-px bg-white/10" />
                                <span className="absolute px-4 bg-transparent text-xs text-white/20 uppercase tracking-widest backdrop-blur-md">Or continue with</span>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <motion.button
                                    whileHover={{ y: -3 }}
                                    className="flex items-center justify-center gap-2 glass-card py-3 rounded-xl hover:bg-white/10 transition-colors"
                                >
                                    <Chrome className="w-5 h-5 text-white" />
                                    <span className="text-sm font-medium">Google</span>
                                </motion.button>
                                <motion.button
                                    whileHover={{ y: -3 }}
                                    className="flex items-center justify-center gap-2 glass-card py-3 rounded-xl hover:bg-white/10 transition-colors"
                                >
                                    <Github className="w-5 h-5 text-white" />
                                    <span className="text-sm font-medium">GitHub</span>
                                </motion.button>
                            </div>
                        </div>

                        <div className="mt-10 text-center">
                            <button
                                onClick={() => setIsLogin(!isLogin)}
                                className="text-white/40 text-sm hover:text-white transition-colors"
                            >
                                {isLogin ? "Don't have an account? " : "Already have an account? "}
                                <span className="text-yt-red font-bold underline decoration-red-500/30 underline-offset-4">
                                    {isLogin ? 'Sign Up' : 'Sign In'}
                                </span>
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            </div>
        </div>
    );
};

export default LoginPage;
