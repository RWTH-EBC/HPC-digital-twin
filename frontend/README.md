# IT-Zauber Dashboard

Welcome to the development of **IT-Zauber Dashboard**! This project template is a modern web application built using best-practice technologies like **React.js**, **Next.js**, **TailwindCSS**, **Shadcn UI**, and **Recharts**. This README will help you understand the project's structure, provide setup instructions, guide you through the tools and how to implement new components.

---

## Table of Contents

1. [Template Overview](#template-overview)
2. [Getting Started](#getting-started)
3. [Documentation Links](#documentation-links)
4. [Why this Template utilizes primarily Typescript?](#why-this-template-utilizes-primarily-typescript)
5. [Why update to React 19](#why-update-to-react-19)
6. [TSX and JSX Compatibility](#tsx-and-jsx-compatibility)
7. [Contributing](#contributing)

---

## Template Overview

This dashboard is designed to provide a visually appealing, responsive, and highly interactive user experience. It utilizes powerful UI libraries and a streamlined development process to deliver seamless functionality.

### UI/UX Features

- **Components, Blocks, Themes and Charts**: Built-in Shadcn-UI [Components](https://ui.shadcn.com/docs/components/card), [Blocks](https://ui.shadcn.com/blocks), [Themes](https://ui.shadcn.com/themes) and [Charts](https://ui.shadcn.com/charts).
- **Icons**: Beautiful and scalable icons using [Lucide-react](https://lucide.dev/icons/).
- **Customize charts**: Customize the Recharts based Shadcn-UI charts using [Recharts](https://recharts.org/en-US/storybook).
- **Customize UI**: Customize UI with [TailwindCSS](https://tailwindcss.com/docs/border-style).

#### Further Features

- Frontend - [React 19](https://react.dev/reference/react)
- Framework - [Next.js 15](https://nextjs.org)
- Language - [TypeScript](https://www.typescriptlang.org/docs/handbook/intro.html)
- Linting - [ESLint](https://eslint.org)
- Formatting - [Prettier](https://prettier.io)

---

## Getting Started

### Prerequisites

- **Node.js**: Version 16 or higher
- **npm**: Version 7 or higher
- A code editor like **VS Code**

### Installation

1. Clone the repository:

   ```bash
   git clone https://git-ce.rwth-aachen.de/it-zauber/react-dashboard-frontend.git
   cd IT-Zauber-dashboard
   ```

2. Install dependencies:

   ```bash
   npm install
   npm audit fix
   ```

3. Start the development server:

    ```bash
    npm run dev
    ```

4. Open your browser and navigate to `http://localhost:3000`.

You can start editing the page by modifying `src/app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/basic-features/font-optimization) to automatically optimize and load Inter, a custom Google Font.

---

## Documentation Links

### **Next.js**

A React-based framework for building server-rendered applications.
[Next.js Documentation](https://nextjs.org/docs)

### **ShadCN UI**

ShadCN UI provides composable and accessible components that integrate seamlessly with TailwindCSS and Recharts.  
Components: [ShadCN UI Components](https://ui.shadcn.com/docs/components/card) Blocks: [Blocks](https://ui.shadcn.com/blocks), Themes: [Themes](https://ui.shadcn.com/themes) and Charts: [Charts](https://ui.shadcn.com/charts).

### **TailwindCSS**

TailwindCSS is a utility-first CSS framework for rapid UI development.  
Documentation: [TailwindCSS Documentation](https://tailwindcss.com/docs/border-style)

### **Lucide Icons**

Lucide is an open-source icon library designed for React.  
Documentation: [Lucide Icons Documentation](https://lucide.dev/icons/)

### **Recharts**

A composable charting library for React which is integrate seamlessly in ShadCN UI.  
[Recharts Documentation](https://recharts.org/en-US/)

### **React**

React is a Typescript and JavaScript library for building user interfaces.  
Documentation: [React Documentation](https://react.dev)

---

## Why this Template utilizes primarily Typescript

TypeScript is a superset of JavaScript that adds **static typing** and **type checking**. It helps catch errors early during development, improving the robustness and maintainability of your code.

TypeScript is a statically compiled programming language for writing clear and concise JavaScript code. It’s fulfilling the same purpose as JavaScript and can be used for both client-side and server-side applications. In addition, the libraries of JavaScript are also compatible with TypeScript. In other words, TypeScript is JavaScript with some additional features.

### Benefits of TypeScript

- Type Safety
- Better IDE Support (Autocomplete, Refactoring)
- Scalability for larger projects
- Catch runtime errors at compile time

---

## TSX and JSX Compatibility

TSX and JSX files are compatible in one Project. This means an external .js File from another Project can be reused by just renaming the File to .jsx.

### **What is JSX?**

JSX stands for **JavaScript XML**. It allows you to write HTML-like syntax directly in JavaScript files, making it easier to create React components.

### **What is TSX?**

TSX is the TypeScript extension of JSX. It supports all JSX features while allowing TypeScript's type-checking capabilities.

### Compatibility

- `.jsx` files are written using plain JavaScript.
- `.tsx` files are written using TypeScript and support type definitions.

---

## Why update to React 19

**New use Hook**: Simplifies data fetching by allowing components to directly await Promises, reducing boilerplate and improving Suspense compatibility. Watch here [React 19 New](https://www.youtube.com/watch?v=qWPInECvNRo).

---

## Scripts in `package.json`

- **`npm run dev`**: Starts the development server.
- **`npm run build`**: Builds the application for production.
- **`npm run start`**: Starts the production server.
- **`npm run lint`**: Runs the linter for code quality.

---

## Contributing

If you'd like to contribute, please fork the repository, create a new branch and make a pull request with your changes.
Feel free to explore and enhance the project! Happy coding! 🚀

### Dashboard Pages

| Pages| Directory|
| :--- | :--- |
| Home | src/app/page.tsx |
| Dashboard | src/app/scenario/page.tsx |
| Optimierung | src/app/optimizer/page.tsx |
| Settings | src/app/settings/page.tsx |
| | |

### Project Directory Structure

| Folder| Explanation|
| :--- | :--- |
| src/components/ui | contains all installed ShadCN UI Standard Components |
| src/components | contains all App Components build with ShadCN UI Standard Components |
| src/components/charts | contains all Charts build with ShadCN UI Standard chart |
| | |

```plaintext
SHADCN-DASHBOARD/
├── .next/
├── node_modules/
├── public/
├── src/
│   ├── app/
│   │   ├── optimizer/
│   │   ├── scenario/
│   │   ├── settings/
│   │   ├── favicon.ico
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── charts/
│   │   │   ├── MultipleLineChart.tsx
│   │   │   └── PerformanceChart.tsx
│   │   ├── ui/
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── chart.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── input.tsx
│   │   │   ├── separator.tsx
│   │   │   ├── sheet.tsx
│   │   │   ├── sidebar.tsx
│   │   │   ├── skeleton.tsx
│   │   │   ├── table.tsx
│   │   │   ├── tooltip.tsx
│   │   ├── app-sidebar.tsx
│   │   ├── card.tsx
│   │   ├── DataTable.tsx
│   │   ├── mode-toggle.tsx
│   │   ├── PageTitle.tsx
│   │   ├── theme-provider.tsx
│   │   └── hooks/
│   │       └── use-mobile.tsx
│   ├── lib/
│   │   └── utils.ts
├── .eslintc.json
├── .gitignore
├── components.json
├── next-env.d.ts
├── next.config.js
├── package-lock.json
├── package.json
├── postcss.config.js
├── README.md
├── tailwind.config.js
└── tsconfig.json
```

## How to Implement a New Next.js Component in the DASHBOARD Project

For the beginning you can watch [How To Make Beautiful Charts](https://www.youtube.com/watch?v=15qMh8C1Wzo&t=542s) or use the [ShadCN UI](#shadcn-ui)  documentations.
Follow these steps to create and integrate a new component into the project:

---

### File Creation

Create a new `.tsx` file in components folder or a subfolder, e.g., `src/components/MyComponent.tsx`.

---

### Write the Component Code

- Use a functional component with TypeScript for type safety.
- Define props using an interface.

Example:

```tsx
import React from "react";

interface MyComponentProps {
  title: string;
  onClick: () => void;
}

const MyComponent: React.FC<MyComponentProps> = ({ title, onClick }) => {
  return (
    <button
      onClick={onClick}
      className="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600"
    >
      {title}
    </button>
  );
};

export default MyComponent;
```

#### **Styling**

- Use **TailwindCSS** for in-line styling.
- Utilize any pre-configured utility classes like `globals.css` if applicable.

#### **Accessibility**

- Ensure the component is accessible (e.g., use ARIA attributes if needed).

#### **Testing**

- Add basic functionality checks (manually or through tests).

---

### Import and Use the Component

1. **Import the Component**:
   - Import the component where it is needed:

     ```tsx
     import MyComponent from "@/components/ui/MyComponent";
     ```

2. **Use the Component**:
   - Pass props and integrate it into the layout:

     ```tsx
     <MyComponent title="Click Me" onClick={() => alert("Button Clicked")} />
     ```

---

### Documentation and Comments

- Add comments to explain the purpose of the component and its props.
- If the component is reusable, document usage in the README or a dedicated `docs` folder.

---

### Follow Project Conventions

#### Linting and Formatting

- Ensure the component adheres to ESLint rules by running:

  ```bash
  npm run lint
  ```

#### Testing Integration

- Verify manually the component behaves as expected in local development server by running:

  ```bash
  npm run dev
  ```

  You should now be able to access the application at [http://localhost:3000](http://localhost:3000).

#### Theming

- Ensure the you build your components with ShadCN UI components, to support light and dark theme.

---

### Commit and Push

1. **Commit Changes**:
   - Commit the component file with a meaningful message:

     ```bash
     git add .
     git commit -m "Add MyComponent for reusable button functionality"
     ```

2. **Push to Repository**:

   ```bash
   git push origin [branch-name]
   ```
