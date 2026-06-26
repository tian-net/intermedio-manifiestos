# Video Script - ELCHINO Restobar Full Stack Web Application

**Total Duration:** ~4-5 minutes
**Language:** English
**Format:** Group presentation, each member presents 1-2 slides

---

## Slide 1 - Cover (30s)

**Speaker 1:**
> "Hello everyone. Today we are presenting ELCHINO Restobar, a full-stack web application designed to digitize restaurant operations. This project was built using MongoDB, Spring Boot WebFlux, React, and deployed on AWS EC2 with Minikube."

---

## Slide 2 - Table of Contents (15s)

**Speaker 1:**
> "We will cover the problem we aimed to solve, the Google Workspace technologies we used for collaboration, the architecture of our application, how it works, a live demonstration, and our conclusions."

---

## Slide 3 - The Problem (45s)

**Speaker 2:**
> "Before this project, the restaurant operated with manual processes. Orders were written on paper, menus were static PDFs, and customer data was scattered across spreadsheets. There was no centralized system, which led to errors, delays, and lost information. The restaurant needed a digital platform that would allow customers to browse the menu online, place orders digitally, and enable staff to manage everything from a single interface. Additionally, the solution needed to be scalable for future growth."

---

## Slide 4 - Google Workspace Technologies (30s)

**Speaker 2:**
> "For this project, we used several Google Workspace tools. Google Slides for creating this presentation collaboratively. Google Docs for writing our technical report and documentation in real-time. Google Drive to store and share screenshots, diagrams, and project assets. And Gmail for team communication, notifications, and coordinating our work."

---

## Slide 5 - Architecture Overview (45s)

**Speaker 3:**
> "Our architecture consists of three EC2 instances running on AWS, all within the same VPC. EC2-1 hosts MongoDB 7 on Minikube, serving as our database. EC2-2 runs the backend, a Spring Boot WebFlux application with reactive MongoDB driver. EC2-3 hosts the frontend, a React application built with Vite and served by Nginx. Each instance is a t3.medium with 4GB of RAM and 2 vCPUs, running Minikube with Docker driver."

---

## Slide 6 - How It Works: Flow (45s)

**Speaker 3:**
> "The user flow is straightforward. A customer opens the web application in their browser, accessing the frontend on EC2-3. The React interface communicates with the backend API on EC2-2 via HTTP. The backend, built with Spring Boot WebFlux, processes requests using reactive programming, which allows it to handle many concurrent connections efficiently. When data is needed, the backend queries MongoDB on EC2-1 using the reactive MongoDB driver for non-blocking database access. The response travels back through the same path to the user."

---

## Slide 7 - Technical Details (45s)

**Speaker 4:**
> "Let's look at the technical details of each component. The frontend was built with Vite for fast development and bundled with Nginx for production. The API URL is configured through an environment variable, making deployment flexible. The backend uses Spring Boot WebFlux, which is fully reactive and non-blocking. It exposes RESTful endpoints for CRUD operations on products, categories, and orders. MongoDB 7 runs in a container on Minikube with persistent storage. We seeded the database with initial data for testing. The entire infrastructure runs on AWS EC2 with NodePort services exposing each component."

---

## Slide 8 - Demonstration (45s)

**Speaker 4:**
> "Now let's see the application in action. [Show screenshot 1] Here is the frontend interface where users can browse the menu and place orders. [Show screenshot 2] Here is an example API response from our backend, showing products in JSON format. [Show screenshot 3] And here we can see the MongoDB seed data properly loaded in the database with collections for categories, products, and orders."

---

## Slide 9 - Conclusions (30s)

**Speaker 1:**
> "In conclusion, we built a modern, cloud-native architecture using industry-standard technologies. The application is scalable, maintainable, and provides an end-to-end solution for the restaurant. And through Google Workspace, we were able to collaborate effectively as a team."

---

## Slide 10 - Thank You (15s)

**All speakers together:**
> "Thank you for your attention. We are happy to answer any questions."

---

## Production Notes

- **Each speaker should face the camera when speaking**
- **Share screen** showing the slides during the presentation
- **Transition between speakers** smoothly: "And now I'll pass to [name] who will explain..."
- **Speak clearly and at a moderate pace**
- **Total time:** ~4-5 minutes (adjust based on actual recording)
